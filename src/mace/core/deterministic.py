import hashlib
import hmac
import datetime
import random
import os

# Global state
_seed = None
_mode = "NORMAL"  # "NORMAL" or "DETERMINISTIC"

# Counters
_counters = {
    "id": 0,
    "sem_write": 0,
    "log": 0
}

def init_seed(seed):
    """
    Initialize the global seed and reset counters.
    seed: int or string
    """
    global _seed, _counters
    if isinstance(seed, int):
        _seed = str(seed)
    else:
        _seed = seed
    
    # Reset counters
    # We must reset ALL counters, including dynamic ones like percept_time
    _counters = {}
    
    # If in deterministic mode, seed Python's random too (optional but good for safety)
    if _mode == "DETERMINISTIC":
        random.seed(_seed)

def set_mode(mode):
    """
    Set the operating mode.
    mode: "NORMAL" or "DETERMINISTIC"
    """
    global _mode
    if mode not in ["NORMAL", "DETERMINISTIC"]:
        raise ValueError("Invalid mode. Must be 'NORMAL' or 'DETERMINISTIC'.")
    _mode = mode

def get_mode():
    return _mode

def get_seed():
    return _seed

def increment_counter(counter_name):
    """
    Increment a specific counter and return the new value.
    """
    if counter_name not in _counters:
        _counters[counter_name] = 0
    _counters[counter_name] += 1
    return _counters[counter_name]

def deterministic_timestamp(counter=None):
    """
    Generate a deterministic ISO8601 timestamp based on the seed and a counter.
    If counter is None, uses the current time (ONLY IN NORMAL MODE).
    In DETERMINISTIC mode, counter is REQUIRED or it will raise an error.
    """
    if _mode == "NORMAL" and counter is None:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    if _seed is None:
        raise RuntimeError("Seed not initialized. Call init_seed() first.")
        
    if counter is None:
        # In deterministic mode, we must have a counter to derive time
        # For safety, we can default to a global time counter if not provided, 
        # but explicit is better. Let's use a dedicated time counter if needed.
        # For now, raise strict error as per spec.
        raise ValueError("Counter required for deterministic_timestamp in DETERMINISTIC mode.")

    # Derive a time offset from the hash of seed + counter
    # User requirement: t = HMAC(seed || counter)
    # We must ensure this is strictly followed.
    
    payload = str(counter).encode('utf-8')
    key = str(_seed).encode('utf-8')
    h = hmac.new(key, payload, hashlib.sha256).digest()
    
    # Use first 8 bytes to determine seconds offset from a base epoch
    # Base epoch: 2025-01-01T00:00:00Z
    offset_seconds = int.from_bytes(h[:4], 'big') % 315360000 # Cap at ~10 years
    
    base_time = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    derived_time = base_time + datetime.timedelta(seconds=offset_seconds)
    
    return derived_time.isoformat()
