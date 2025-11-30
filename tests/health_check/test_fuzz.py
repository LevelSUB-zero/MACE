import unittest
import json
import os
import random
import string
from mace.core import deterministic, replay
from mace.runtime import executor
from mace.memory import semantic

class TestFuzz(unittest.TestCase):
    
    def setUp(self):
        deterministic.init_seed("fuzz_test_seed")
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")

    def test_9_1_random_seeds_sweep(self):
        """
        9.1 — Random seeds sweep
        For 100 random seeds, run a small set of queries and assert no exceptions and replay passes.
        """
        print("\nRunning Seed Sweep (100 iterations)...")
        
        queries = ["2+2", "what is my favorite_color", "remember my x is y"]
        
        failures = 0
        
        for i in range(100):
            seed = f"fuzz_seed_{i}"
            query = random.choice(queries)
            
            try:
                res, log_entry = executor.execute(query, seed=seed, log_enabled=False)
                
                # Replay
                res_replay = replay.replay_log(log_entry)
                if not res_replay["success"]:
                    raise RuntimeError(f"Replay failed: {res_replay['error']} Details: {res_replay.get('details')}")
                
            except Exception as e:
                print(f"FAIL: Seed {seed}, Query '{query}' -> {e}")
                failures += 1
                
        self.assertEqual(failures, 0, f"Seed sweep failed with {failures} errors")
        print("PASS: Random seeds sweep")

    def test_9_2_large_payload_handling(self):
        """
        9.2 — Large payload handling
        Attempt to put_sem with a very large JSON value (1MB).
        """
        large_str = "a" * (1024 * 1024) # 1MB string
        val = {"data": large_str}
        key = "user/profile/user_99/large_payload"
        
        try:
            res = semantic.put_sem(key, val)
            self.assertTrue(res["success"])
            
            # Verify read
            res_get = semantic.get_sem(key)
            self.assertTrue(res_get["exists"])
            self.assertEqual(len(res_get["value"]["data"]), 1024 * 1024)
            
            print("\nPASS: Large payload handling")
            
        except Exception as e:
            self.fail(f"Large payload caused crash: {e}")

if __name__ == "__main__":
    unittest.main()
