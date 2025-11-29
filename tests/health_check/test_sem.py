import unittest
import json
import os
import time
from mace.core import deterministic
from mace.memory import semantic, storage_backend

class TestSEM(unittest.TestCase):
    
    def setUp(self):
        deterministic.init_seed("sem_test_seed")
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")
        if os.path.exists("logs/sem_write_journal.jsonl"):
            for i in range(5):
                try:
                    os.remove("logs/sem_write_journal.jsonl")
                    break
                except OSError:
                    time.sleep(0.1)

    def test_3_1_put_get_roundtrip(self):
        """
        3.1 — Put/Get roundtrip
        Use put_sem(seed1, key, val). Immediately get_sem.
        """
        key = "user/profile/user_99/favorite_color"
        val = {"value": "indigo"}
        
        res_put = semantic.put_sem(key, val)
        self.assertTrue(res_put["success"])
        
        res_get = semantic.get_sem(key)
        self.assertTrue(res_get["exists"])
        self.assertEqual(res_get["value"], val)
        self.assertEqual(res_get["last_updated"], res_put["last_updated"])
        
        print("\nPASS: SEM Put/Get roundtrip")

    def test_3_2_last_write_wins(self):
        """
        3.2 — Last-write-wins & deterministic timestamps
        put A, then put B under same key. get -> expect B.
        """
        key = "user/profile/user_99/favorite_color"
        val_a = {"value": "green"}
        val_b = {"value": "red"}
        
        # Put A
        res_a = semantic.put_sem(key, val_a)
        
        # Put B
        res_b = semantic.put_sem(key, val_b)
        
        # Get
        res_get = semantic.get_sem(key)
        self.assertEqual(res_get["value"], val_b)
        
        # Check timestamps
        # ISO strings compare lexicographically correctly
        self.assertGreater(res_b["last_updated"], res_a["last_updated"])
        
        print("PASS: SEM Last-write-wins")

    def test_3_4_db_failure(self):
        """
        3.4 — DB failure deterministic handling
        Simulate DB failure. Attempt put_sem.
        """
        # Monkeypatch StorageBackend.put to raise exception
        original_put = storage_backend.StorageBackend.put
        
        def fail_put(self, key, value, timestamp):
            raise RuntimeError("Simulated DB Crash")
            
        storage_backend.StorageBackend.put = fail_put
        
        try:
            key = "user/profile/user_99/fail_test"
            val = {"value": "test"}
            
            res = semantic.put_sem(key, val)
            
            # Should return deterministic error
            self.assertFalse(res["success"])
            self.assertEqual(res["error"], "Simulated DB Crash")
            
            print("PASS: SEM DB failure handling")
            
        finally:
            # Restore
            storage_backend.StorageBackend.put = original_put

if __name__ == "__main__":
    unittest.main()
