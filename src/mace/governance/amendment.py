import json
import os

AMENDMENTS_FILE = "amendments.jsonl"

def load_amendments():
    """
    Load active amendments from file.
    Returns list of amendment dicts.
    """
    amendments = []
    if os.path.exists(AMENDMENTS_FILE):
        try:
            with open(AMENDMENTS_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        amendments.append(json.loads(line))
        except:
            pass # Fail open if file corrupt? Or fail closed? Stage-0: ignore errors.
    return amendments

def check_policy(policy_type, target):
    """
    Check if a target is blocked by any active amendment.
    
    Args:
        policy_type (str): "block_key", "block_agent", etc.
        target (str): The value to check (e.g. key name).
        
    Returns:
        bool: True if BLOCKED, False if ALLOWED.
    """
    amendments = load_amendments()
    for amd in amendments:
        if not amd.get("active", True):
            continue
            
        if amd.get("policy_type") == policy_type:
            # Check target match
            # Exact match for now
            if amd.get("target") == target:
                return True
                
    return False
