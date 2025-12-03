import unittest
import os
import sqlite3
import json
import sys
sys.path.append(os.getcwd())
from migrations import migrate_template

class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_stage1.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
    def test_migration_and_tables(self):
        """Verify DDL execution and table creation."""
        sql_file = "migrations/0001_create_stage1_tables.sql"
        
        # Run migration
        migrate_template.run_migration_sqlite(self.db_path, sql_file)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check tables exist
        tables = ["self_representation_nodes", "self_representation_edges", 
                  "apt_events", "reflective_logs", "episodic", "admin_tokens"]
        
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            self.assertIsNotNone(cursor.fetchone(), f"Table {table} missing")
            
        # Test Insert
        node_json = json.dumps({"status": "active"})
        cursor.execute("INSERT INTO self_representation_nodes (module_id, node_json, created_at, version) VALUES (?, ?, ?, ?)",
                       ("mod_1", node_json, "2025-01-01T00:00:00Z", 1))
        
        conn.commit()
        
        # Test Select
        cursor.execute("SELECT module_id, node_json FROM self_representation_nodes WHERE module_id='mod_1'")
        row = cursor.fetchone()
        self.assertEqual(row[0], "mod_1")
        self.assertEqual(row[1], node_json)
        
        conn.close()

if __name__ == "__main__":
    unittest.main()
