import unittest
import os
import json
from mace.apt import engine
import sys
sys.path.append(os.getcwd())
from migrations import migrate_template
from mace.core import deterministic

class TestAPT(unittest.TestCase):
    def setUp(self):
        self.db_path = "mace_stage1.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        # Init DB
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0001_create_stage1_tables.sql")
        migrate_template.run_migration_sqlite(self.db_path, "migrations/0002_gap_remediation.sql")
        
        # Init seed
        deterministic.init_seed("test_apt_seed")
        
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
    def test_log_and_get(self):
        # Log events
        e1_id = engine.log_event("node_a", "TEST_EVENT", {"foo": "bar"})
        e2_id = engine.log_event("node_b", "TEST_EVENT", {"baz": "qux"})
        
        # Get events
        events = engine.get_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event_id"], e1_id)
        self.assertEqual(events[0]["sequence_idx"], 1)
        self.assertEqual(events[1]["event_id"], e2_id)
        self.assertEqual(events[1]["sequence_idx"], 2)
        
    def test_replay(self):
        engine.log_event("node_a", "E1", {"val": 1})
        engine.log_event("node_a", "E2", {"val": 2})
        engine.log_event("node_a", "E3", {"val": 3})
        
        replayed = []
        def handler(event):
            replayed.append(event["payload"]["val"])
            
        engine.replay_events(1, 3, handler)
        self.assertEqual(replayed, [1, 2, 3])
        
        replayed_partial = []
        def handler_partial(event):
            replayed_partial.append(event["payload"]["val"])
            
        engine.replay_events(2, 2, handler_partial)
        self.assertEqual(replayed_partial, [2])

if __name__ == "__main__":
    unittest.main()
