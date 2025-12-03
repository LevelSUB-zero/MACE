import json
import datetime
from mace.core import persistence, deterministic, canonical

class EpisodicMemory:
    def __init__(self):
        pass
        
    def add_episode(self, summary, payload, job_seed=None):
        """
        Persist an episode.
        """
        conn = persistence.get_connection()
        try:
            # Generate ID
            if deterministic.get_seed() is None and job_seed:
                deterministic.init_seed(job_seed)
            elif deterministic.get_seed() is None:
                deterministic.init_seed("episodic_fallback")
                
            payload_json = canonical.canonical_json_serialize(payload)
            episodic_id = deterministic.deterministic_id("episodic", payload_json)
            
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            persistence.execute_query(conn,
                "INSERT INTO episodic (episodic_id, summary, payload, created_seeded_ts) VALUES (?, ?, ?, ?)",
                (episodic_id, summary, payload_json, timestamp)
            )
            conn.commit()
            return episodic_id
        finally:
            conn.close()
            
    def get_episode(self, episodic_id):
        conn = persistence.get_connection()
        try:
            cur = persistence.execute_query(conn, "SELECT * FROM episodic WHERE episodic_id = ?", (episodic_id,))
            row = persistence.fetch_one(cur)
            if row:
                return {
                    "episodic_id": row["episodic_id"],
                    "summary": row["summary"],
                    "payload": json.loads(row["payload"]),
                    "created_at": row["created_seeded_ts"]
                }
            return None
        finally:
            conn.close()
