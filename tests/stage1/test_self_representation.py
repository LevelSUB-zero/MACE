import unittest
import os
import json
import sqlite3
from mace.self_representation import core
import sys
sys.path.append(os.getcwd())
from migrations import migrate_template
from mace.core import deterministic

class TestSelfRepresentation(unittest.TestCase):
    def setUp(self):
        self.db_path = "mace_stage1.db" # Default used by persistence helper
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        # Init DB
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0001_create_stage1_tables.sql")
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0002_gap_remediation.sql")
        
        # Init seed
        deterministic.init_seed("test_seed")
        
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
    def test_register_and_get(self):
        module = {
            "module_id": "test_agent",
            "version": "1.0.0",
            "capabilities": ["test"],
            "status": "active"
        }
        
        # Register
        core.register_module(module)
        
        # Get
        retrieved = core.get_module("test_agent")
        self.assertEqual(retrieved["module_id"], "test_agent")
        self.assertEqual(retrieved["status"], "active")
        
    def test_decommission(self):
        module = {
            "module_id": "test_agent_2",
            "version": "1.0.0",
            "capabilities": [],
            "status": "active"
        }
        core.register_module(module)
        
        # Decommission
        success = core.decommission_module("test_agent_2")
        self.assertTrue(success)
        
        # Verify status
        retrieved = core.get_module("test_agent_2")
        self.assertEqual(retrieved["status"], "offline")
        
    def test_snapshot(self):
        m1 = {"module_id": "a", "version": "1", "capabilities": [], "status": "active"}
        m2 = {"module_id": "b", "version": "1", "capabilities": [], "status": "active"}
        
        core.register_module(m1)
        core.register_module(m2)
        
        snap = core.graph_snapshot()
        self.assertIsNotNone(snap["snapshot_id"])
        self.assertEqual(len(snap["snapshot"]["nodes"]), 2)
        self.assertEqual(snap["snapshot"]["nodes"][0]["module_id"], "a")

if __name__ == "__main__":
    unittest.main()
