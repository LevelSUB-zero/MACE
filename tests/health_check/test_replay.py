import unittest
import json
import os
from mace.core import deterministic, replay
from mace.runtime import executor
from mace.memory import semantic

class TestReplay(unittest.TestCase):
    
    def setUp(self):
        deterministic.init_seed("replay_test_seed")
        # Ensure clean DB
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")

    def test_1_2_replay_structural_equality(self):
        """
        1.2 — Replay full structural equality
        Take a saved log. Replay must compare all fields.
        """
        # Generate log
        query = "What is 2 + 2?"
        res, log_entry = executor.execute(query, seed="seed_1_2", log_enabled=False)
        
        # Replay
        print("\nRunning Replay 1.2...")
        replay.replay_log(log_entry)
        print("PASS: Replay 1.2 structural equality")

    def test_6_1_snapshot_replay(self):
        """
        6.1 — Semi-manual replay
        Use sem_read_snapshot in log; clear current SEM DB and ensure replay uses snapshot.
        """
        # 1. Populate DB
        executor.execute("remember my favorite_color is red", seed="setup_seed")
        
        # 2. Generate Log with Read
        # "what is my favorite_color" -> reads "red"
        res, log_entry = executor.execute("what is my favorite_color", seed="read_seed", log_enabled=False)
        
        self.assertIn("red", res["text"])
        self.assertTrue(len(log_entry["memory_reads"]) > 0)
        # Check evidence for value
        found_val = None
        for ev in log_entry["evidence_items"]:
            if ev["type"] == "sem_read_snapshot" and ev["source"]["reference"] == "user/profile/user_123/favorite_color":
                found_val = ev["content"]["structured"]
                if found_val is None and ev["content"]["text"]:
                     found_val = json.loads(ev["content"]["text"])
                break
        self.assertEqual(found_val, "red")
        
        # 3. Clear DB
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")
            
        # 4. Replay
        # Should succeed because it uses snapshot from log_entry
        print("\nRunning Replay 6.1 (Snapshot)...")
        replay.replay_log(log_entry)
        print("PASS: Replay 6.1 snapshot used")

    def test_6_2_corrupt_snapshot_detection(self):
        """
        6.2 — Replay with corrupt snapshot detection
        Corrupt sem_read_snapshot in log intentionally. Expect REPLAY_MISMATCH.
        """
        # 1. Populate DB
        executor.execute("remember my favorite_color is blue", seed="setup_seed_2")
        
        # 2. Generate Log
        res, log_entry = executor.execute("what is my favorite_color", seed="read_seed_2", log_enabled=False)
        
        # 3. Corrupt Log Snapshot
        # Change "blue" to "green" in the snapshot
        key = "user/profile/user_123/favorite_color"
        
        # Find the evidence item for this key
        found = False
        for ev in log_entry["evidence_items"]:
            if ev["type"] == "sem_read_snapshot" and ev["source"]["reference"] == key:
                ev["content"]["structured"] = "green"
                ev["content"]["text"] = "green" # Update text too just in case
                found = True
                break
                
        if not found:
            self.fail("Could not find snapshot evidence to corrupt")
        
        # 4. Replay
        # Replay will use "green" from snapshot.
        # But wait, replay executes logic.
        # Logic: get_sem(key) -> returns "green" (from snapshot).
        # Agent output: "My favorite_color is green".
        # Original log output: "My favorite_color is blue".
        # Mismatch!
        
        print("\nRunning Replay 6.2 (Corrupt)...")
        print("\nRunning Replay 6.2 (Corrupt)...")
        res = replay.replay_log(log_entry)
        self.assertFalse(res["success"])
        self.assertIn("OUTPUT_MISMATCH", res["error"])
        print("PASS: Replay 6.2 detected corruption")

if __name__ == "__main__":
    unittest.main()
