import json
import datetime
from mace.core import persistence, deterministic, canonical

def log_event(node_id, event_type, payload):
    """
    Log an event to the APT stream.
    Returns the event_id.
    """
    conn = persistence.get_connection()
    try:
        # 1. Get next sequence index
        # Note: This is a simple implementation. For high concurrency, use DB sequences.
        cur = persistence.execute_query(conn, "SELECT MAX(event_sequence_idx) as max_seq FROM apt_events")
        row = persistence.fetch_one(cur)
        next_seq = (row["max_seq"] if row and row["max_seq"] is not None else 0) + 1
        
        # 2. Generate Deterministic ID
        # We need a seed. If strictly deterministic job, use deterministic.deterministic_id.
        # If system event, maybe use random or time-based?
        # The plan implies strict determinism.
        # Let's assume we are in a context where deterministic.get_seed() is valid or we init one.
        # If not, we might fall back to a system seed.
        
        if deterministic.get_seed() is None:
             # Fallback for system events outside a job context
             # In production, this might be a UUID.
             # For Stage-1, let's use a temporary seed if needed, or just UUID if not strict.
             # But let's try to stick to deterministic_id if possible.
             deterministic.init_seed("apt_system_seed")

        # Payload for ID generation should include seq to be unique
        id_payload = {
            "node_id": node_id,
            "type": event_type,
            "seq": next_seq,
            "payload": payload
        }
        canonical_payload = canonical.canonical_json_serialize(id_payload)
        event_id = deterministic.deterministic_id("apt_event", canonical_payload)
        
        # 3. Insert
        event_json = canonical.canonical_json_serialize(payload)
        
        persistence.execute_query(conn,
            "INSERT INTO apt_events (event_id, node_id, event_json, event_sequence_idx) VALUES (?, ?, ?, ?)",
            (event_id, node_id, event_json, next_seq)
        )
        conn.commit()
        return event_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_events(start_seq=0, end_seq=None):
    """
    Retrieve events in range [start_seq, end_seq].
    """
    conn = persistence.get_connection()
    try:
        query = "SELECT * FROM apt_events WHERE event_sequence_idx >= ?"
        params = [start_seq]
        
        if end_seq is not None:
            query += " AND event_sequence_idx <= ?"
            params.append(end_seq)
            
        query += " ORDER BY event_sequence_idx ASC"
        
        cur = persistence.execute_query(conn, query, tuple(params))
        rows = persistence.fetch_all(cur)
        
        events = []
        for row in rows:
            events.append({
                "event_id": row["event_id"],
                "node_id": row["node_id"],
                "sequence_idx": row["event_sequence_idx"],
                "payload": json.loads(row["event_json"])
            })
        return events
    finally:
        conn.close()

def replay_events(start_seq, end_seq, handler_func):
    """
    Replay events and pass them to a handler function.
    handler_func(event_dict)
    """
    events = get_events(start_seq, end_seq)
    for event in events:
        handler_func(event)
