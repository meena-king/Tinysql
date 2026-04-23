import struct

ROW_FORMAT = '<? I 32s 255s'
ROW_SIZE = struct.calcsize(ROW_FORMAT) # 292 bytes

class Row:
    def __init__(self, id, username, email, is_deleted=False):
        self.is_deleted = is_deleted
        self.id = int(id)
        self.username = username.encode('utf-8')[:32].ljust(32, b'\0')
        self.email = email.encode('utf-8')[:255].ljust(255, b'\0')

    def serialize(self):
        return struct.pack(ROW_FORMAT, self.is_deleted, self.id, self.username, self.email)

    @classmethod
    def deserialize(cls, data):
        unpacked = struct.unpack(ROW_FORMAT, data)
        return cls(
            is_deleted=unpacked[0],
            id=unpacked[1],
            username=unpacked[2].decode('utf-8').rstrip('\0'),
            email=unpacked[3].decode('utf-8').rstrip('\0')
        )