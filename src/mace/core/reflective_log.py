import json
import hmac
import hashlib

def canonical_serialize(obj):
    """
    Serialize object to JSON with deterministic ordering and no whitespace.
    """
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))

def sign_log_entry(entry, secret_key):
    """
    Sign a log entry with HMAC-SHA256.
    Adds 'signature' field to the entry.
    """
    # Remove existing signature if any to avoid double signing
    payload = entry.copy()
    if "signature" in payload:
        del payload["signature"]
        
    serialized = canonical_serialize(payload)
    
    if isinstance(secret_key, str):
        secret_key = secret_key.encode('utf-8')
        
    signature = hmac.new(secret_key, serialized.encode('utf-8'), hashlib.sha256).hexdigest()
    
    entry["signature"] = signature
    return entry

def verify_log_entry(entry, secret_key):
    """
    Verify the signature of a log entry.
    Returns True if valid, False otherwise.
    """
    if "signature" not in entry:
        return False
        
    signature = entry["signature"]
    
    payload = entry.copy()
    del payload["signature"]
    
    serialized = canonical_serialize(payload)
    
    if isinstance(secret_key, str):
        secret_key = secret_key.encode('utf-8')
        
    expected_signature = hmac.new(secret_key, serialized.encode('utf-8'), hashlib.sha256).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

import os
LOG_FILE = "logs/reflective_log.jsonl"

def append_log(entry):
    """
    Append a log entry to the reflective log file.
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
