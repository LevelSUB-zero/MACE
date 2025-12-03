import os
import sys
import json
import argparse

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from mace.core import persistence, signing, canonical

def verify_signatures(db_url=None):
    if db_url:
        os.environ["MACE_DB_URL"] = db_url
        
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn, "SELECT log_id, log_json, immutable_subpayload, signature, signature_key_id FROM reflective_logs")
        rows = persistence.fetch_all(cur)
        
        print(f"Verifying {len(rows)} logs...")
        
        passed = 0
        failed = 0
        
        for row in rows:
            log_id = row["log_id"]
            signature = row["signature"]
            key_id = row["signature_key_id"]
            
            # Reconstruct payload from DB column
            # Note: In Postgres it's JSONB (dict), in SQLite it's TEXT (str).
            subpayload_raw = row["immutable_subpayload"]
            if isinstance(subpayload_raw, str):
                subpayload = json.loads(subpayload_raw)
            else:
                subpayload = subpayload_raw
                
            # Verify
            if signing.verify_signature(subpayload, signature, key_id):
                passed += 1
            else:
                print(f"FAIL: Log {log_id} signature mismatch!")
                failed += 1
                
        print(f"Verification Complete. Passed: {passed}, Failed: {failed}")
        return failed == 0
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="Database URL")
    args = parser.parse_args()
    
    success = verify_signatures(args.db)
    sys.exit(0 if success else 1)
