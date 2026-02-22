import json
import datetime
import copy
from mace.core import persistence, deterministic, canonical, signing

_table_initialized = False

def _ensure_table_exists():
    """Create reflective_logs table if it doesn't exist."""
    global _table_initialized
    if _table_initialized:
        return
    
    conn = persistence.get_connection()
    try:
        persistence.execute_query(conn, """
            CREATE TABLE IF NOT EXISTS reflective_logs (
                log_id TEXT PRIMARY KEY,
                log_json TEXT,
                immutable_subpayload TEXT,
                signature TEXT,
                signature_key_id TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        _table_initialized = True
    finally:
        conn.close()

def write_log(log_entry):
    """
    Write a reflective log entry with signing.
    """
    _ensure_table_exists()
    conn = persistence.get_connection()
    try:
        # 1. Prepare Immutable Subpayload
        # The spec says `immutable_subpayload` contains critical fields to sign.
        # Let's pick: log_id, percept.text, final_output.text, router_decision.decision_id
        
        log_id = log_entry["log_id"]
        
        subpayload = {
            "log_id": log_id,
            "percept_text": log_entry["percept"]["text"],
            "final_output_text": log_entry["final_output"]["text"],
            "router_decision_id": log_entry["router_decision"]["decision_id"]
        }
        
        log_entry["immutable_subpayload"] = subpayload
        
        # 2. Sign
        # We need a key ID.
        key_id = "reflective_log_key"
        signature = signing.sign_payload(subpayload, key_id)
        
        log_entry["signature"] = signature
        log_entry["signature_key_id"] = key_id
        
        # 3. Persist
        log_json = canonical.canonical_json_serialize(log_entry)
        subpayload_json = canonical.canonical_json_serialize(subpayload)
        timestamp = log_entry["timestamp"]
        
        persistence.execute_query(conn,
            "INSERT INTO reflective_logs (log_id, log_json, immutable_subpayload, signature, signature_key_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (log_id, log_json, subpayload_json, signature, key_id, timestamp)
        )
        conn.commit()
        return True
    finally:
        conn.close()
