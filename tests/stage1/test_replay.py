import unittest
import os
import json
from mace.runtime import executor
from mace.replay import replay
from mace.core import persistence, deterministic
import sys
sys.path.append(os.getcwd())
from migrations import migrate_template
# Import tools logic
from tools import verify_signatures

class TestReplay(unittest.TestCase):
    def setUp(self):
        self.db_path = "mace_stage1.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0001_create_stage1_tables.sql")
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0002_gap_remediation.sql")
        deterministic.init_seed("replay_test_seed")
        
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
    def test_replay_fidelity(self):
        # 1. Execute
        # Use intent="math" and input "2+2" to trigger math agent
        output, log_entry = executor.execute("2+2", intent="math")
        
        # 2. Replay
        result = replay.replay_log(log_entry)
        
        if not result["success"]:
            print(f"\nReplay Error Details: {result.get('details')}")
        self.assertTrue(result["success"], f"Replay failed: {result.get('error')}")
        
    def test_signature_verification(self):
        # 1. Execute
        executor.execute("2+2", intent="math")
        
        # 2. Verify
        # We need to set env var for the tool function
        os.environ["MACE_DB_URL"] = f"sqlite:///{self.db_path}"
        success = verify_signatures.verify_signatures()
        self.assertTrue(success)

if __name__ == "__main__":
    unittest.main()
