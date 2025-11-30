import unittest
import os
import hashlib
import json
from mace.core import deterministic, replay
from mace.runtime import executor
from mace.memory import semantic

class TestReplaySideEffects(unittest.TestCase):
    
    def setUp(self):
        deterministic.init_seed("side_effect_test")
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")
        if os.path.exists("logs/sem_write_journal.jsonl"):
            os.remove("logs/sem_write_journal.jsonl")

    def calculate_file_hash(self, filepath):
        if not os.path.exists(filepath):
            return None
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def test_replay_no_db_writes(self):
        """
        Verify that replaying a log entry that contains a write operation
        does NOT modify the underlying SQLite database file.
        """
        # 1. Generate a log with a write
        print("\nGenerating log with write...")
        res, log_entry = executor.execute("remember my secret is safe", seed="write_seed")
        
        self.assertTrue(res["text"].startswith("Stored"))
        
        # Ensure DB exists
        self.assertTrue(os.path.exists("mace_memory.db"))
        
        # 2. Snapshot DB state
        initial_hash = self.calculate_file_hash("mace_memory.db")
        print(f"Initial DB Hash: {initial_hash}")
        
        # 3. Replay
        print("Replaying...")
        result = replay.replay_log(log_entry)
        self.assertTrue(result["success"], f"Replay failed: {result.get('error')}")
        
        # 4. Verify DB state
        final_hash = self.calculate_file_hash("mace_memory.db")
        print(f"Final DB Hash:   {final_hash}")
        
        self.assertEqual(initial_hash, final_hash, "DB file was modified during replay!")
        
    def test_replay_sandbox_isolation(self):
        """
        Verify that replay writes do not overwrite existing data in the live DB,
        even if the data differs.
        """
        # 1. Generate log: "remember x is A"
        res, log_entry = executor.execute("remember my x is A", seed="iso_seed_1")
        
        # 2. Manually change DB: "x is B"
        # We use a new seed to ensure different timestamp if we were using it, 
        # but here we just want to change the value.
        semantic.put_sem("user/profile/user_123/x", "B")
        
        # Verify DB has "B"
        val = semantic.get_sem("user/profile/user_123/x")
        self.assertEqual(val["value"], "B")
        
        # 3. Replay log (which tries to write "A")
        # Replay should succeed (it writes "A" to sandbox)
        # But Live DB should still have "B"
        result = replay.replay_log(log_entry)
        self.assertTrue(result["success"])
        
        # 4. Verify Live DB still has "B"
        val_after = semantic.get_sem("user/profile/user_123/x")
        self.assertEqual(val_after["value"], "B", "Replay overwrote live DB!")

if __name__ == "__main__":
    unittest.main()
