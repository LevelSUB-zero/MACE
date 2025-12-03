import unittest
import os
from mace.memory import wm, cwm, episodic
from mace.brainstate import brainstate
from mace.core import deterministic
import sys
sys.path.append(os.getcwd())
from migrations import migrate_template

class TestMemoryLayers(unittest.TestCase):
    def setUp(self):
        self.db_path = "mace_stage1.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0001_create_stage1_tables.sql")
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0002_gap_remediation.sql")
        deterministic.init_seed("mem_seed")
        
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
    def test_wm(self):
        bs = brainstate.create_snapshot("seed1")
        w = wm.WorkingMemory(bs)
        w.add_item("test_content", "m1")
        
        items = w.get_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["content"], "test_content")
        
    def test_cwm(self):
        c = cwm.ConsolidatedWorkingMemory()
        c.add_item({"id": 1})
        self.assertEqual(len(c.get_items()), 1)
        
    def test_episodic(self):
        e = episodic.EpisodicMemory()
        eid = e.add_episode("summary", {"data": 123})
        
        retrieved = e.get_episode(eid)
        self.assertEqual(retrieved["summary"], "summary")
        self.assertEqual(retrieved["payload"]["data"], 123)

if __name__ == "__main__":
    unittest.main()
