import struct
from models import ROW_SIZE

PAGE_SIZE = 4096

# ==========================================
# PAGE HEADER LAYOUT CONCEPTS
# ==========================================
# Byte 0: Node Type (0 = Internal, 1 = Leaf)
# Bytes 1-4: Number of Cells (How many rows are currently on this page?)
# Bytes 5-8: Next Leaf Node (Page number of the sibling leaf, for range queries)

# 'B' means 1-byte unsigned char. 'I' means 4-byte unsigned integer.
HEADER_FORMAT = '<B I I' 
HEADER_SIZE = struct.calcsize(HEADER_FORMAT) # 1 + 4 + 4 = 9 bytes!

LEAF_MAX_CELLS = (PAGE_SIZE - HEADER_SIZE) // ROW_SIZE # (4096 - 9) // 292 = 13 rows per page

class LeafNode:
    """
    This is a 'Utility Class'. It doesn't store data itself. 
    It just provides methods to easily manipulate the raw bytearray of a page.
    """
    
    @staticmethod
    def initialize(page_bytearray):
        """Takes a blank 4096-byte array and paints the 'Leaf Node Label' on it."""
        node_type = 1  # 1 = Leaf Node
        num_cells = 0  # Starts completely empty
        next_leaf = 0  # 0 means there is no next page yet
        
        # Pack these 3 numbers into exactly 9 bytes and put them at the very start of the page
        struct.pack_into(HEADER_FORMAT, page_bytearray, 0, node_type, num_cells, next_leaf)

    @staticmethod
    def get_num_cells(page_bytearray):
        """Reads Bytes 1-4 to tell us how many rows are currently saved here."""
        # offset=1 skips the 1-byte Node Type to read the Number of Cells
        return struct.unpack_from('<I', page_bytearray, offset=1)[0]

    @staticmethod
    def set_num_cells(page_bytearray, num_cells):
        """Updates Bytes 1-4 when we insert or delete a row."""
        struct.pack_into('<I', page_bytearray, 1, num_cells)

    @staticmethod
    def get_cell_offset(cell_index):
        """
        Calculates the exact byte coordinate where a specific row lives.
        Row 0 starts exactly at Byte 9 (right after the header).
        """
        return HEADER_SIZE + (cell_index * ROW_SIZE)

    @staticmethod
    def insert_row(page_bytearray, cell_index, serialized_row):
        """Writes a 292-byte row into the correct slot on the page."""
        offset = LeafNode.get_cell_offset(cell_index)
        page_bytearray[offset : offset + ROW_SIZE] = serialized_row
        
        # Increase the cell count by 1 in the header
        current_cells = LeafNode.get_num_cells(page_bytearray)
        LeafNode.set_num_cells(page_bytearray, current_cells + 1)


# ==========================================
# INTERNAL NODE CONCEPTS (The Directory)
# ==========================================
# An internal node doesn't hold 292-byte rows. It holds tiny 8-byte "Cells"
# (4 bytes for an ID, 4 bytes for a Page Number).

INTERNAL_HEADER_FORMAT = '<B I I' # Type (0), Num Keys, Rightmost Child Page
INTERNAL_HEADER_SIZE = struct.calcsize(INTERNAL_HEADER_FORMAT)
INTERNAL_CELL_FORMAT = '<I I' # Key (ID), Left Child Page
INTERNAL_CELL_SIZE = struct.calcsize(INTERNAL_CELL_FORMAT)

class InternalNode:
    @staticmethod
    def initialize(page_bytearray):
        node_type = 0  # 0 = Internal Node (Directory)
        num_keys = 0
        right_child = 0
        struct.pack_into(INTERNAL_HEADER_FORMAT, page_bytearray, 0, node_type, num_keys, right_child)

    @staticmethod
    def get_num_keys(page_bytearray):
        return struct.unpack_from('<I', page_bytearray, offset=1)[0]

    @staticmethod
    def set_num_keys(page_bytearray, num_keys):
        struct.pack_into('<I', page_bytearray, 1, num_keys)

    @staticmethod
    def set_right_child(page_bytearray, page_num):
        struct.pack_into('<I', page_bytearray, 5, page_num)
        
    @staticmethod
    def get_right_child(page_bytearray):
        return struct.unpack_from('<I', page_bytearray, offset=5)[0]

    @staticmethod
    def get_cell_offset(cell_index):
        return INTERNAL_HEADER_SIZE + (cell_index * INTERNAL_CELL_SIZE)

    @staticmethod
    def insert_key_and_pointer(page_bytearray, cell_index, key, left_child_page):
        offset = InternalNode.get_cell_offset(cell_index)
        struct.pack_into(INTERNAL_CELL_FORMAT, page_bytearray, offset, key, left_child_page)
        
        current_keys = InternalNode.get_num_keys(page_bytearray)
        InternalNode.set_num_keys(page_bytearray, current_keys + 1)