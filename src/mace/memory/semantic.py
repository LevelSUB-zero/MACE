
import re
import json
import os
import hashlib
from mace.core import deterministic
from mace.memory import storage_backend
from mace.governance import amendment
from mace.ops import metrics

# Regex for canonical key validation (Strict 4-segment)
CANONICAL_KEY_REGEX = re.compile(r"^([a-z0-9_]+)\/([a-z0-9_]+)\/([a-z0-9_\-]+)\/([a-z0-9_]+)$")

# Global journal file
JOURNAL_FILE = "logs/sem_write_journal.jsonl"
SYNONYMS_FILE = "sem_synonyms.json"

# Capture context for replay/logging
_capture_context = None

# Storage Abstraction
class LiveSEMStore:
    def get(self, key):
        backend = storage_backend.StorageBackend()
        val_str, ts = backend.get(key)
        backend.close()
        return val_str, ts

    def put(self, key, value_str, timestamp):
        backend = storage_backend.StorageBackend()
        success = backend.put(key, value_str, timestamp)
        backend.close()
        return success

    def is_sandbox(self):
        return False

class ReplaySEMStore:
    def __init__(self, snapshot=None):
        self.snapshot = snapshot if snapshot else {}
        self.writes = {} # Ephemeral writes {key: val_str}

    def get(self, key):
        # 1. Check writes (read-your-writes)
        if key in self.writes:
            return self.writes[key], deterministic.deterministic_timestamp()
        
        # 2. Check snapshot
        if key in self.snapshot:
            # Snapshot values are already objects, need to serialize to match LiveStore interface
            # or handle object return. LiveStore returns string.
            # Let's return string to be consistent.
            val = self.snapshot[key]
            return json.dumps(val), "REPLAY_SNAPSHOT"
            
        return None, None

    def put(self, key, value_str, timestamp):
        self.writes[key] = value_str
        return True

    def is_sandbox(self):
        return True

# Active Store
_active_store = LiveSEMStore()

def set_store(store):
    global _active_store
    _active_store = store

def start_capture():
    global _capture_context
    _capture_context = {
        "reads": {}, 
        "writes": []
    }

def stop_capture():
    global _capture_context
    captured = _capture_context
    _capture_context = None
    return captured

def generate_canonical_key(raw_key):
    """
    Generate a canonical key from a raw string.
    """
    # 1. Lowercase
    key = raw_key.lower()
    
    # 2. Replace spaces with underscores
    key = key.replace(" ", "_")
    
    # 3. Remove non-alphanumeric (except _, ., :, /, -)
    key = re.sub(r"[^a-z0-9_./:\-]", "", key)
    
    # 4. Max length 64 chars
    if len(key) > 64:
        key = key[:64]
        
    return key

def sem_resolve_alias(text, user_id="user_id"):
    """
    Resolve a natural language text to a canonical key using synonyms.
    """
    synonyms = {}
    if os.path.exists(SYNONYMS_FILE):
        try:
            with open(SYNONYMS_FILE, "r") as f:
                synonyms = json.load(f)
        except:
            pass
            
    if text in synonyms:
        resolved = synonyms[text]
        resolved = resolved.replace("user_id", user_id)
        return resolved
        
    return generate_canonical_key(text)

def _validate_key(key):
    # Regex: category/subcategory/namespace/name
    # All segments: a-z0-9_ (namespace can have -)
    pattern = r"^([a-z0-9_]+)\/([a-z0-9_]+)\/([a-z0-9_\-]+)\/([a-z0-9_]+)$"
    if not re.match(pattern, key):
        raise ValueError(f"Invalid canonical key format: {key}")
    return True

def _append_to_journal(entry):
    if _active_store.is_sandbox():
        return # No journaling in sandbox
    os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)
    with open(JOURNAL_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def _check_pii(value_str):
    # Simple regex for PII (e.g. CC, SSN)
    # Also check for explicit "PII" string for testing
    if "PII" in value_str:
        return True
    # Credit Card (simple)
    if re.search(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", value_str):
        return True
    # SSN
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", value_str):
        return True
    return False

def put_sem(key, value, source="unknown"):
    """
    Write a value to Semantic Memory.
    """
    try:
        # 1. Validate Key
        try:
            _validate_key(key)
        except ValueError:
            return {"success": False, "error": "INVALID_KEY_FORMAT"}
        
        # Governance Check
        if amendment.check_policy("block_key", key):
            return {"success": False, "error": "POLICY_BLOCKED"}
        
        # 3. Serialize & Check PII
        val_str = json.dumps(value)
        if _check_pii(val_str):
            return {"success": False, "error": "PRIVACY_BLOCKED"}
        
        # 4. Deterministic Metadata
        write_counter = deterministic.increment_counter("sem_write")
        ts = deterministic.deterministic_timestamp(write_counter)
        value_hash = hashlib.sha256(val_str.encode('utf-8')).hexdigest()
        
        # 5. Write to Active Store
        success = _active_store.put(key, val_str, ts)
        
        if success:
            metrics.increment("sem_writes_total")
            
            write_id = deterministic.deterministic_id("sem_write", key, write_counter)
            
            entry = {
                "write_id": write_id,
                "canonical_key": key,
                "value_hash": value_hash,
                "source": source,
                "last_updated": ts,
                "seed": deterministic.get_seed(),
                "write_counter": write_counter,
                "op": "PUT",
                "value_snapshot": value
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
    """
    try:
        # Delegate to Active Store
        val_str, last_updated = _active_store.get(key)
        
        if val_str is not None:
            val = json.loads(val_str)
            metrics.increment("sem_reads_total")
            
            if _capture_context is not None:
                _capture_context["reads"][key] = {"value": val, "exists": True}
                
            return {
                "exists": True,
                "value": val,
                "last_updated": last_updated
            }
        else:
            if _capture_context is not None:
                _capture_context["reads"][key] = {"value": None, "exists": False}
                
            return {"exists": False, "value": None, "last_updated": None}
            
    except Exception as e:
        return {"exists": False, "value": None, "last_updated": None}
