import json
import os
from mace.core import deterministic

LOG_FILE = "logs/reflective_log.jsonl"

def append_log(entry):
    """
    Append a ReflectiveLogEntry to the log file.
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # Ensure entry is JSON serializable
    # (Assuming entry is a dict from structures.create_reflective_log_entry)
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
        
def get_logs():
    """
    Generator to read logs.
    """
    if not os.path.exists(LOG_FILE):
        return
        
    with open(LOG_FILE, "r") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)
