import os
import sys
import json
import argparse

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from mace.core import persistence
from mace.replay import replay

def verify_replay(log_id, db_url=None):
    if db_url:
        os.environ["MACE_DB_URL"] = db_url
        
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn, "SELECT log_json FROM reflective_logs WHERE log_id = ?", (log_id,))
        row = persistence.fetch_one(cur)
        
        if not row:
            print(f"Log {log_id} not found.")
            return False
            
        log_json = row["log_json"]
        if isinstance(log_json, str):
            log_entry = json.loads(log_json)
        else:
            log_entry = log_json
            
        print(f"Replaying log {log_id}...")
        result = replay.replay_log(log_entry)
        
        if result["success"]:
            print("SUCCESS: Replay matched original log.")
            return True
        else:
            print(f"FAIL: Replay failed. Error: {result['error']}")
            if "details" in result:
                print(f"Details: {result['details']}")
            return False
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("log_id", help="Log ID to replay")
    parser.add_argument("--db", help="Database URL")
    args = parser.parse_args()
    
    success = verify_replay(args.log_id, args.db)
    sys.exit(0 if success else 1)
