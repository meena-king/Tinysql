from models import Row, ROW_SIZE
from pager import PAGE_SIZE
from btree_node import LeafNode, InternalNode, LEAF_MAX_CELLS

class BTreeEngine:
    def __init__(self, pager):
        self.pager = pager
        
        if self.pager.num_pages == 0:
            print("Initializing B+ Tree Database Root Node...")
            root_page = bytearray(b'\0' * PAGE_SIZE)
            LeafNode.initialize(root_page)
            self.pager.write_page(0, bytes(root_page))

    def _get_node_type(self, page_data):
        return page_data[0]

    def insert(self, row):
        root_data = bytearray(self.pager.read_page(0))
        node_type = self._get_node_type(root_data)

        if node_type == 1: # Leaf Node
            num_cells = LeafNode.get_num_cells(root_data)
            
            if num_cells >= LEAF_MAX_CELLS:
                print("\n[SYSTEM] Page 0 is full! Splitting the Root Node...")
                self._split_root_leaf(root_data)
                self.insert(row)
                return

            insert_index = num_cells
            for i in range(num_cells):
                offset = LeafNode.get_cell_offset(i)
                temp_row = Row.deserialize(root_data[offset : offset + ROW_SIZE])
                if temp_row.id > row.id:
                    insert_index = i
                    break 

            if insert_index < num_cells:
                src_start = LeafNode.get_cell_offset(insert_index)
                src_end = LeafNode.get_cell_offset(num_cells)
                root_data[src_start + ROW_SIZE : src_end + ROW_SIZE] = root_data[src_start:src_end]

            LeafNode.insert_row(root_data, insert_index, row.serialize())
            self.pager.write_page(0, bytes(root_data))

        else:  # Internal Node — traverse to the correct leaf and insert there
            import struct
            current_page_num = 0
            while True:
                page_data = bytearray(self.pager.read_page(current_page_num))
                node_type = self._get_node_type(page_data)
                if node_type == 1:
                    break  # reached a leaf
                num_keys = InternalNode.get_num_keys(page_data)
                found_path = False
                for i in range(num_keys):
                    offset = InternalNode.get_cell_offset(i)
                    key = struct.unpack_from('<I', page_data, offset)[0]
                    left_child = struct.unpack_from('<I', page_data, offset + 4)[0]
                    if row.id < key:
                        current_page_num = left_child
                        found_path = True
                        break
                if not found_path:
                    current_page_num = InternalNode.get_right_child(page_data)

            # page_data is now the target leaf; insert in sorted order
            leaf_data = bytearray(self.pager.read_page(current_page_num))
            num_cells = LeafNode.get_num_cells(leaf_data)
            insert_index = num_cells
            for i in range(num_cells):
                offset = LeafNode.get_cell_offset(i)
                temp_row = Row.deserialize(leaf_data[offset: offset + ROW_SIZE])
                if temp_row.id > row.id:
                    insert_index = i
                    break
            if insert_index < num_cells:
                src_start = LeafNode.get_cell_offset(insert_index)
                src_end   = LeafNode.get_cell_offset(num_cells)
                leaf_data[src_start + ROW_SIZE: src_end + ROW_SIZE] = leaf_data[src_start:src_end]
            LeafNode.insert_row(leaf_data, insert_index, row.serialize())
            self.pager.write_page(current_page_num, bytes(leaf_data))
            print(f"[SYSTEM] Inserted ID {row.id} into leaf page {current_page_num}.")

    def _split_root_leaf(self, old_root_data):
        left_page_num = self.pager.num_pages
        right_page_num = self.pager.num_pages + 1
        
        left_data = bytearray(b'\0' * PAGE_SIZE)
        right_data = bytearray(b'\0' * PAGE_SIZE)
        LeafNode.initialize(left_data)
        LeafNode.initialize(right_data)

        middle_index = LEAF_MAX_CELLS // 2
        middle_offset = LeafNode.get_cell_offset(middle_index)
        middle_row = Row.deserialize(old_root_data[middle_offset : middle_offset + ROW_SIZE])
        middle_id = middle_row.id

        for i in range(middle_index):
            offset = LeafNode.get_cell_offset(i)
            LeafNode.insert_row(left_data, i, old_root_data[offset : offset + ROW_SIZE])

        for i in range(middle_index, LEAF_MAX_CELLS):
            offset = LeafNode.get_cell_offset(i)
            LeafNode.insert_row(right_data, i - middle_index, old_root_data[offset : offset + ROW_SIZE])

        self.pager.write_page(left_page_num, bytes(left_data))
        self.pager.write_page(right_page_num, bytes(right_data))

        new_root_data = bytearray(b'\0' * PAGE_SIZE)
        InternalNode.initialize(new_root_data)
        
        InternalNode.insert_key_and_pointer(new_root_data, 0, middle_id, left_page_num)
        InternalNode.set_right_child(new_root_data, right_page_num)

        self.pager.write_page(0, bytes(new_root_data))
        print(f"[SYSTEM] Root split complete! Middle ID '{middle_id}' promoted to Directory.")

    def find(self, search_id):
        import struct
        current_page_num = 0
        
        while True:
            page_data = self.pager.read_page(current_page_num)
            node_type = self._get_node_type(page_data)
            
            if node_type == 1: 
                break 
                
            num_keys = InternalNode.get_num_keys(page_data)
            found_path = False
            
            for i in range(num_keys):
                offset = InternalNode.get_cell_offset(i)
                key = struct.unpack_from('<I', page_data, offset)[0]
                left_child = struct.unpack_from('<I', page_data, offset + 4)[0]
                
                if search_id < key:
                    current_page_num = left_child
                    found_path = True
                    break
                    
            if not found_path:
                current_page_num = InternalNode.get_right_child(page_data)

        num_cells = LeafNode.get_num_cells(page_data)
        for i in range(num_cells):
            offset = LeafNode.get_cell_offset(i)
            row_bytes = page_data[offset : offset + ROW_SIZE]
            row = Row.deserialize(row_bytes)
            
            if not row.is_deleted and row.id == search_id:
                return row
            
            if row.id > search_id:
                break
                
        return None

    def delete(self, search_id):
        import struct
        current_page_num = 0
        
        while True:
            page_data = bytearray(self.pager.read_page(current_page_num))
            node_type = self._get_node_type(page_data)
            
            if node_type == 1: 
                break 
                
            num_keys = InternalNode.get_num_keys(page_data)
            found_path = False
            
            for i in range(num_keys):
                offset = InternalNode.get_cell_offset(i)
                key = struct.unpack_from('<I', page_data, offset)[0]
                left_child = struct.unpack_from('<I', page_data, offset + 4)[0]
                
                if search_id < key:
                    current_page_num = left_child
                    found_path = True
                    break
                    
            if not found_path:
                current_page_num = InternalNode.get_right_child(page_data)

        num_cells = LeafNode.get_num_cells(page_data)
        for i in range(num_cells):
            offset = LeafNode.get_cell_offset(i)
            row_bytes = page_data[offset : offset + ROW_SIZE]
            row = Row.deserialize(row_bytes)
            
            if not row.is_deleted and row.id == search_id:
                row.is_deleted = True
                page_data[offset : offset + ROW_SIZE] = row.serialize()
                self.pager.write_page(current_page_num, bytes(page_data))
                return True
            
            if row.id > search_id:
                break 
                
        return False