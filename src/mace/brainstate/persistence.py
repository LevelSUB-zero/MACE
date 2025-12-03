"""
BrainState persistence layer for Stage-1.
Handles save/load of brain state snapshots to/from database.
"""
import json
from mace.core import persistence, canonical

def save_snapshot(brainstate):
    """
    Persist BrainState snapshot to database.
    """
    conn = persistence.get_connection()
    try:
        snapshot_id = brainstate["snapshot_id"]
        job_seed = brainstate.get("job_seed", "unknown")
        created_at = brainstate.get("created_at", "")
        tick_count = brainstate.get("tick_count", 0)
        
        # Canonicalize before storage
        brainstate_json = canonical.canonical_json_serialize(brainstate)
        
        # Upsert (insert or replace)
        persistence.execute_query(conn,
            "INSERT OR REPLACE INTO brainstate_snapshots (snapshot_id, job_seed, brainstate_json, created_at, tick_count) VALUES (?, ?, ?, ?, ?)",
            (snapshot_id, job_seed, brainstate_json, created_at, tick_count)
        )
        conn.commit()
        return snapshot_id
    finally:
        conn.close()

def load_latest_snapshot(job_seed=None):
    """
    Load the most recent BrainState snapshot, optionally filtered by job_seed.
    Returns None if no snapshots exist.
    """
    conn = persistence.get_connection()
    try:
        if job_seed:
            cur = persistence.execute_query(conn,
                "SELECT brainstate_json FROM brainstate_snapshots WHERE job_seed = ? ORDER BY created_at DESC LIMIT 1",
                (job_seed,)
            )
        else:
            cur = persistence.execute_query(conn,
                "SELECT brainstate_json FROM brainstate_snapshots ORDER BY created_at DESC LIMIT 1"
            )
        
        row = persistence.fetch_one(cur)
        if not row:
            return None
        
        brainstate_json = row["brainstate_json"]
        
        # Handle both string (SQLite) and dict (Postgres JSONB)
        if isinstance(brainstate_json, str):
            return json.loads(brainstate_json)
        else:
            return brainstate_json
    finally:
        conn.close()

def get_snapshot_by_id(snapshot_id):
    """
    Retrieve a specific BrainState snapshot by ID.
    """
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn,
            "SELECT brainstate_json FROM brainstate_snapshots WHERE snapshot_id = ?",
            (snapshot_id,)
        )
        row = persistence.fetch_one(cur)
        if not row:
            return None
        
        brainstate_json = row["brainstate_json"]
        if isinstance(brainstate_json, str):
            return json.loads(brainstate_json)
        else:
            return brainstate_json
    finally:
        conn.close()
