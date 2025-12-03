import unittest
import os
import json
from mace.runtime import executor
from mace.core import persistence, deterministic
import sys
sys.path.append(os.getcwd())
from migrations import migrate_template

class TestExecutor(unittest.TestCase):
    def setUp(self):
        self.db_path = "mace_stage1.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0001_create_stage1_tables.sql")
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0002_gap_remediation.sql")
        deterministic.init_seed("exec_seed")
        
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
    def test_execution_cycle(self):
        # Run execution
        output, log_entry = executor.execute("2+2", intent="math")
        
        # Verify output
        self.assertIn("4", output["text"])
        
        # Verify log entry
        self.assertIsNotNone(log_entry)
        self.assertIn("signature", log_entry)
        self.assertIn("immutable_subpayload", log_entry)
        
        # Verify persistence
        conn = persistence.get_connection()
        cur = persistence.execute_query(conn, "SELECT * FROM reflective_logs WHERE log_id = ?", (log_entry["log_id"],))
        row = persistence.fetch_one(cur)
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row["signature"], log_entry["signature"])
        
    def test_router_selection(self):
        # Should pick profile agent
        output, log_entry = executor.execute("Update my profile", intent="profile")
        
        decision = log_entry["router_decision"]
        self.assertEqual(decision["selected_agents"][0]["agent_id"], "profile_agent")

if __name__ == "__main__":
    unittest.main()
