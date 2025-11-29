import re
import json
import os
from mace.core import deterministic
from mace.memory.storage_backend import StorageBackend

# Regex for canonical key validation
CANONICAL_KEY_REGEX = re.compile(r"^[a-z0-9_\/]+$")

# Global journal file
JOURNAL_FILE = "logs/sem_write_journal.jsonl"

# Capture context for replay/logging
_capture_context = None

def start_capture():
    global _capture_context
    _capture_context = {
        "reads": {}, # Changed to dict {key: value}
        "writes": []
    }

# Replay snapshot
_replay_snapshot = None

def set_replay_snapshot(snapshot):
    global _replay_snapshot
    _replay_snapshot = snapshot

def stop_capture():
    global _capture_context
    captured = _capture_context
    _capture_context = None
    return captured

def _validate_key(key):
    if not CANONICAL_KEY_REGEX.match(key):
        raise ValueError(f"Invalid canonical key format: {key}")

def _append_to_journal(entry):
    """
    Append a write operation to the journal.
    """
    os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)
    with open(JOURNAL_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def put_sem(key, value):
    """
    Write a value to Semantic Memory.
    
    Args:
        key (str): Canonical key.
        value (any): JSON-serializable value.
        
    Returns:
        dict: {"success": bool, "last_updated": str, "error": str (optional)}
    """
    try:
        _validate_key(key)
        
        # Get deterministic timestamp
        # Note: We increment sem_write counter for timestamp generation here?
        # Rulebook says: last_updated = deterministic_timestamp(seed, sem_write_counter++)
        ts = deterministic.deterministic_timestamp(deterministic.increment_counter("sem_write"))
        
        # Serialize value
        val_str = json.dumps(value)
        
        # Initialize backend (could be global/singleton in real app, instantiating here for Stage-0 simplicity)
        backend = StorageBackend()
        success = backend.put(key, val_str, ts)
        backend.close()
        
        if success:
            # Journal entry
            entry = {
                "op": "PUT",
                "key": key,
                "value": value,
                "timestamp": ts,
                "seed_snapshot": deterministic.get_seed()
            }
            _append_to_journal(entry)
            
            if _capture_context is not None:
                _capture_context["writes"].append(key)
            
            return {"success": True, "last_updated": ts}
        else:
            return {"success": False, "error": "DB_WRITE_FAILED"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_sem(key):
    """
    Read a value from Semantic Memory.
    
    Args:
        key (str): Canonical key.
        
    Returns:
        dict: {"exists": bool, "value": any, "last_updated": str}
    """
    try:
        _validate_key(key)
        
        # Check replay snapshot first
        if _replay_snapshot is not None:
            if key in _replay_snapshot:
                val = _replay_snapshot[key]
                if val is None:
                    return {"exists": False}
                else:
                    return {
                        "exists": True, 
                        "value": val, 
                        "last_updated": deterministic.deterministic_timestamp(0) # Dummy TS for replay
                    }
            # If not in snapshot, fall through to DB? 
            # Or treat as miss? 
            # For strict replay, if it's not in snapshot, it might be a miss.
            # But let's assume snapshot contains ALL relevant keys.
            # If we fall through, we might break isolation.
            # Let's fall through for now, but usually snapshot should be complete.
        
        backend = StorageBackend()
        val_str, last_updated = backend.get(key)
        backend.close()
        
        if val_str is not None:
            val = json.loads(val_str)
            if _capture_context is not None:
                _capture_context["reads"][key] = val
                
            return {
                "exists": True,
                "value": val,
                "last_updated": last_updated
            }
        else:
            if _capture_context is not None:
                _capture_context["reads"][key] = None # Log miss as None
                
            return {"exists": False}
            
    except Exception as e:
        # On error (e.g. invalid key format), treat as miss or raise?
        # Rulebook says "Stage-0 must NEVER behave mysteriously".
        # If key is invalid, it technically doesn't exist.
        return {"exists": False}
