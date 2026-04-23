import os

PAGE_SIZE = 4096

class Pager:
    def __init__(self, filename):
        self.filename = filename
        self.fd = os.open(filename, os.O_RDWR | os.O_CREAT)
        self.file_length = os.lseek(self.fd, 0, os.SEEK_END)
        self.num_pages = (self.file_length + PAGE_SIZE - 1) // PAGE_SIZE 
        
        # ADD THIS: Track how many times we hit the disk!
        self.read_count = 0

    def read_page(self, page_num):
        self.read_count += 1 # ADD THIS: Count every read!
        offset = page_num * PAGE_SIZE
        os.lseek(self.fd, offset, os.SEEK_SET)
        data = os.read(self.fd, PAGE_SIZE)
        return data.ljust(PAGE_SIZE, b'\0') 

    def write_page(self, page_num, data):
        offset = page_num * PAGE_SIZE
        os.lseek(self.fd, offset, os.SEEK_SET)
        os.write(self.fd, data[:PAGE_SIZE])
        
        new_length = os.lseek(self.fd, 0, os.SEEK_END)
        self.file_length = new_length
        self.num_pages = (self.file_length + PAGE_SIZE - 1) // PAGE_SIZE

    def close(self):
        os.close(self.fd)