import json
from mace.core import persistence
from mace.brainstate import brainstate

def rebuild_brainstate(job_id):
    """
    Reconstruct BrainState from episodic memory for a specific job.
    Returns reconstructed brainstate dict or None if no data.
    """
    conn = persistence.get_connection()
    try:
        # Query episodic entries matching job_seed pattern
        cur = persistence.execute_query(conn, 
            "SELECT * FROM episodic WHERE job_seed = ? ORDER BY created_seeded_ts ASC",
            (job_id,)
        )
        rows = persistence.fetch_all(cur)
        
        if not rows:
            return None
        
        # Start with fresh state
        bs = brainstate.create_snapshot(job_id)
        
        # Replay episodic entries to rebuild state
        for row in rows:
            payload = row["payload"]
            
            # Handle both JSON string (SQLite) and dict (Postgres)
            if isinstance(payload, str):
                try:
                    episode_data = json.loads(payload)
                except:
                    continue
            else:
                episode_data = payload
            
            # Extract state info from episode
            # Episodes might contain goals, WM items, or other state
            if isinstance(episode_data, dict):
                # If episode has goals, add them
                if "goals" in episode_data:
                    for goal in episode_data["goals"]:
                        if goal not in bs["goals"]:
                            bs["goals"].append(goal)
                
                # If episode has WM items, add them
                if "working_memory" in episode_data:
                    for item in episode_data["working_memory"]:
                        brainstate.add_wm_item(bs, item)
                
                # If episode records a complete brainstate, use it
                if "snapshot_id" in episode_data and "tick_count" in episode_data:
                    # This episode is a brainstate snapshot
                    bs = episode_data
        
        return bs
    finally:
        conn.close()

def load_last_snapshot():
    """
    Load the most recent valid brainstate snapshot.
    Uses the new persistence layer.
    """
    from mace.brainstate import persistence as bs_persistence
    return bs_persistence.load_latest_snapshot()
