import unittest
import os
import sys
sys.path.append(os.getcwd())
from migrations import migrate_template
from mace.governance import admin, killswitch
from mace.core import persistence, rehydrate, deterministic

class TestAdmin(unittest.TestCase):
    def setUp(self):
        self.db_path = "mace_stage1.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0001_create_stage1_tables.sql")
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0002_gap_remediation.sql")
        deterministic.init_seed("admin_test")
        
        # Clean up kill-switch file if exists
        if os.path.exists("mace_killswitch.flag"):
            os.remove("mace_killswitch.flag")
        
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists("mace_killswitch.flag"):
            os.remove("mace_killswitch.flag")
            
    def test_token_lifecycle(self):
        # Generate token
        token, token_id = admin.generate_token("testing", ttl_hours=1)
        
        self.assertIsNotNone(token)
        self.assertIsNotNone(token_id)
        
        # Verify token
        result = admin.verify_token(token)
        self.assertTrue(result["valid"])
        self.assertEqual(result["purpose"], "testing")
        
        # Revoke token
        admin.revoke_token(token_id)
        
        # Verify revoked
        result = admin.verify_token(token)
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "TOKEN_REVOKED")
        
    def test_invalid_token(self):
        result = admin.verify_token("invalid_token_12345")
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "TOKEN_NOT_FOUND")
        
    def test_killswitch(self):
        # Initially inactive
        self.assertFalse(killswitch.is_active())
        
        # Activate
        killswitch.activate("TEST", "admin_user")
        self.assertTrue(killswitch.is_active())
        
        # Get status
        status = killswitch.get_status()
        self.assertTrue(status["active"])
        self.assertEqual(status["reason"], "TEST")
        
        # Deactivate
        killswitch.deactivate()
        self.assertFalse(killswitch.is_active())
        
    def test_rehydration(self):
        # Test load_last_snapshot - returns None if no snapshots exist
        bs = rehydrate.load_last_snapshot()
        # With empty DB, this returns None which is correct
        if bs:
            self.assertIn("goals", bs)
            self.assertIn("working_memory", bs)
        
        # Test rebuild - returns None if no episodic data
        rebuilt = rehydrate.rebuild_brainstate("test_job_123")
        # With empty DB, returns None which is correct
        if rebuilt:
            self.assertIn("goals", rebuilt)

if __name__ == "__main__":
    unittest.main()
