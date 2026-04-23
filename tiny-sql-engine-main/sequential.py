from models import Row, ROW_SIZE
from pager import PAGE_SIZE

class SequentialEngine:
    def __init__(self, pager):
        self.pager = pager
        self.rows_per_page = PAGE_SIZE // ROW_SIZE

    def insert(self, row):
        total_rows = self.pager.file_length // ROW_SIZE
        page_num = total_rows // self.rows_per_page
        row_offset = (total_rows % self.rows_per_page) * ROW_SIZE

        page_data = bytearray(self.pager.read_page(page_num))

        serialized_row = row.serialize()
        page_data[row_offset : row_offset + ROW_SIZE] = serialized_row

        self.pager.write_page(page_num, bytes(page_data))

    def find(self, search_id):
        total_rows = self.pager.file_length // ROW_SIZE
        
        for i in range(total_rows):
            page_num = i // self.rows_per_page
            row_offset = (i % self.rows_per_page) * ROW_SIZE
            
            page_data = self.pager.read_page(page_num)
            row_bytes = page_data[row_offset : row_offset + ROW_SIZE]
            
            if len(row_bytes) == ROW_SIZE:
                row = Row.deserialize(row_bytes)
                # Check that it exists AND is not marked as deleted
                if not row.is_deleted and row.id == search_id:
                    return row 
        
        return None 

    def delete(self, search_id):
        total_rows = self.pager.file_length // ROW_SIZE
        
        for i in range(total_rows):
            page_num = i // self.rows_per_page
            row_offset = (i % self.rows_per_page) * ROW_SIZE
            
            page_data = bytearray(self.pager.read_page(page_num))
            row_bytes = page_data[row_offset : row_offset + ROW_SIZE]
            
            if len(row_bytes) == ROW_SIZE:
                row = Row.deserialize(row_bytes)
                if not row.is_deleted and row.id == search_id:
                    # 1. Flip the flag (Tombstone)
                    row.is_deleted = True
                    # 2. Overwrite the slot
                    page_data[row_offset : row_offset + ROW_SIZE] = row.serialize()
                    # 3. Save to disk
                    self.pager.write_page(page_num, bytes(page_data))
                    return True # Successfully deleted
        
        return False # Not found