from models import Row, ROW_SIZE
from pager import PAGE_SIZE

class HashEngine:
    def __init__(self, pager, num_buckets=100):
        self.pager = pager
        self.num_buckets = num_buckets
        self.rows_per_page = PAGE_SIZE // ROW_SIZE
        
        # Pre-allocate buckets if the file is new
        if self.pager.num_pages < self.num_buckets:
            print(f"Initializing Hash Database with {self.num_buckets} empty buckets...")
            empty_page = b'\0' * PAGE_SIZE
            for i in range(self.num_buckets):
                self.pager.write_page(i, empty_page)

    def hash_id(self, row_id):
        return row_id % self.num_buckets

    def insert(self, row):
        start_page = self.hash_id(row.id)
        current_page = start_page
        
        while True:
            page_data = bytearray(self.pager.read_page(current_page))
            
            for i in range(self.rows_per_page):
                row_offset = i * ROW_SIZE
                slot_bytes = page_data[row_offset : row_offset + ROW_SIZE]
                
                # Look for a totally empty slot
                if slot_bytes == b'\0' * ROW_SIZE:
                    page_data[row_offset : row_offset + ROW_SIZE] = row.serialize()
                    self.pager.write_page(current_page, bytes(page_data))
                    return True
            
            # Linear Probing: Bucket is full, try the next one
            current_page = (current_page + 1) % self.num_buckets
            
            if current_page == start_page:
                raise Exception("Hash Database is completely full!")

    def find(self, search_id):
        start_page = self.hash_id(search_id)
        current_page = start_page
        
        while True:
            page_data = self.pager.read_page(current_page)
            
            for i in range(self.rows_per_page):
                row_offset = i * ROW_SIZE
                slot_bytes = page_data[row_offset : row_offset + ROW_SIZE]
                
                if slot_bytes == b'\0' * ROW_SIZE:
                    return None # Hit an empty slot, row does not exist
                    
                row = Row.deserialize(slot_bytes)
                if not row.is_deleted and row.id == search_id:
                    return row 
            
            current_page = (current_page + 1) % self.num_buckets
            
            if current_page == start_page:
                return None 

    def delete(self, search_id):
        start_page = self.hash_id(search_id)
        current_page = start_page
        
        while True:
            page_data = bytearray(self.pager.read_page(current_page))
            
            for i in range(self.rows_per_page):
                row_offset = i * ROW_SIZE
                slot_bytes = page_data[row_offset : row_offset + ROW_SIZE]
                
                if slot_bytes == b'\0' * ROW_SIZE:
                    return False # Hit an empty slot, row does not exist
                    
                row = Row.deserialize(slot_bytes)
                if not row.is_deleted and row.id == search_id:
                    # 1. Flip the flag
                    row.is_deleted = True
                    # 2. Overwrite the slot
                    page_data[row_offset : row_offset + ROW_SIZE] = row.serialize()
                    # 3. Save to disk
                    self.pager.write_page(current_page, bytes(page_data))
                    return True 
            
            current_page = (current_page + 1) % self.num_buckets
            if current_page == start_page:
                return False