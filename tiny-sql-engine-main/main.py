import sys
import time
from models import Row
from pager import Pager
from sequential import SequentialEngine
from hash_engine import HashEngine 
from btree_engine import BTreeEngine

def main():
    # Setup Sequential DB
    seq_pager = Pager("sequential_data.db")
    seq_engine = SequentialEngine(seq_pager)
    
    # Setup Hash DB
    hash_pager = Pager("hash_data.db") 
    hash_engine = HashEngine(hash_pager, num_buckets=100) 
    
    # Setup B+ Tree DB
    btree_pager = Pager("btree_data.db")
    btree_engine = BTreeEngine(btree_pager)
    
    print("🚀 TinySQL Benchmarker Started.")
    print("Commands:")
    print("  insert [seq|hash|btree] [id] [user] [email]")
    print("  find [seq|hash|btree] [id]")
    print("  delete [seq|hash|btree] [id]")
    print("  .exit")

    while True:
        try:
            user_input = input("TinySQL> ").strip()
        except EOFError:
            break

        if not user_input:
            continue

        if user_input == ".exit":
            seq_pager.close()
            hash_pager.close() 
            btree_pager.close() # <-- Add this
            print("Database closed. Goodbye!")
            sys.exit(0)
            
        parts = user_input.split()
        command = parts[0].lower()

        # --- INSERT ---
        if command == "insert" and len(parts) == 5:
            method, row_id, user, email = parts[1].lower(), parts[2], parts[3], parts[4]
            try:
                row = Row(row_id, user, email)
                if method == "seq":
                    seq_engine.insert(row)
                    print("Inserted into Sequential DB.")
                elif method == "hash": 
                    hash_engine.insert(row)
                    print("Inserted into Hash DB.")
                elif method == "btree": 
                    btree_engine.insert(row)
                    print("Inserted into B+ Tree DB.")
                else:
                    print(f"Engine '{method}' not implemented yet.")
            except ValueError:
                print("Error: ID must be an integer.")

        # --- FIND ---
        elif command == "find" and len(parts) == 3:
            method, search_id = parts[1].lower(), int(parts[2])
            
            start_time = time.perf_counter()
            result = None
            
            # Figure out which pager we are using to track stats
            active_pager = None
            if method == "seq":
                active_pager = seq_pager
            elif method == "hash": 
                active_pager = hash_pager
            elif method == "btree": 
                active_pager = btree_pager
            else:
                print(f"Engine '{method}' not implemented yet.")
                continue

            # Record the read count BEFORE we search
            start_reads = active_pager.read_count
            
            # Run the search
            if method == "seq":
                result = seq_engine.find(search_id)
            elif method == "hash": 
                result = hash_engine.find(search_id)
            elif method == "btree": 
                result = btree_engine.find(search_id)
                
            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000
            
            # Calculate how many pages we read during this specific search
            pages_read = active_pager.read_count - start_reads
            
            # Get the physical file size in KB
            import os
            file_size_kb = os.path.getsize(active_pager.filename) / 1024

            if result:
                print(f"Found: ID: {result.id}, User: {result.username}")
            else:
                print("Row not found.")
                
            # Print the beautiful new benchmark stats!
            print(f"[{method.upper()} BENCHMARK] Time: {elapsed_ms:.4f} ms | Disk Reads: {pages_read} pages | File Size: {file_size_kb:.1f} KB")

        # --- DELETE ---
        elif command == "delete" and len(parts) == 3:
            method, search_id = parts[1].lower(), int(parts[2])
            
            start_time = time.perf_counter()
            success = False
            
            if method == "seq":
                success = seq_engine.delete(search_id)
            elif method == "hash":
                success = hash_engine.delete(search_id)
            elif method == "btree":  # <-- ADD THIS LINE
                success = btree_engine.delete(search_id) # <-- ADD THIS LINE
            else:
                print(f"Engine '{method}' not implemented yet.")
                continue
                
            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000

            if success:
                print(f"Row {search_id} successfully deleted.")
            else:
                print(f"Error: Row {search_id} not found.")
            print(f"[{method.upper()}] Delete Time: {elapsed_ms:.4f} ms")

        else:
            print("Invalid command syntax.")

if __name__ == "__main__":
    main()