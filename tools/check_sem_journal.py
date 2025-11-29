import json
import sys
import os
from mace.memory.storage_backend import StorageBackend

JOURNAL_FILE = "logs/sem_write_journal.jsonl"

def check_consistency():
    if not os.path.exists(JOURNAL_FILE):
        print(f"Journal file {JOURNAL_FILE} not found.")
        return
        
    backend = StorageBackend()
    
    mismatches = 0
    checked = 0
    
    with open(JOURNAL_FILE, "r") as f:
        for line in f:
            entry = json.loads(line)
            if entry["op"] == "PUT":
                key = entry["key"]
                ts = entry["timestamp"]
                
                # Check DB
                val_str, last_updated = backend.get(key)
                
                if val_str is None:
                    print(f"MISMATCH: Key {key} in journal but missing in DB.")
                    mismatches += 1
                else:
                    # DB timestamp must be >= journal timestamp (since journal is append log of writes)
                    # If DB has older timestamp, it means a newer write was lost?
                    # Or if DB has newer, it means subsequent write happened.
                    # So DB >= Journal is correct.
                    if last_updated < ts:
                        print(f"MISMATCH: Key {key} DB timestamp ({last_updated}) < Journal timestamp ({ts})")
                        mismatches += 1
                
                checked += 1
                
    backend.close()
    
    print(f"Checked {checked} entries.")
    if mismatches == 0:
        print("PASS: Journal consistency check passed.")
        sys.exit(0)
    else:
        print(f"FAIL: Found {mismatches} inconsistencies.")
        sys.exit(1)

if __name__ == "__main__":
    check_consistency()
