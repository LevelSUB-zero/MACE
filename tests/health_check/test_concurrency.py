import unittest
import multiprocessing
import os
import time
from mace.memory import semantic

def worker_write(idx):
    # Each worker writes 10 items
    # We need to ensure we don't use the same global state (counters) if they are not shared.
    # But semantic.put_sem uses deterministic module which has process-local state.
    # So each process will start with seed=None or default.
    # We should init seed in worker.
    from mace.core import deterministic
    deterministic.init_seed(f"worker_{idx}")
    
    for i in range(10):
        key = f"user/profile/user_{idx}/item_{i}"
        semantic.put_sem(key, f"value_{idx}_{i}")

class TestConcurrency(unittest.TestCase):
    def test_concurrent_writes(self):
        # 4 workers
        processes = []
        for i in range(4):
            p = multiprocessing.Process(target=worker_write, args=(i,))
            processes.append(p)
            p.start()
            
        for p in processes:
            p.join()
            
        # Verify
        # Total writes = 4 * 10 = 40
        
        # We need to re-init seed for main process to read?
        # Reading doesn't require seed for key lookup, but get_sem might use it for logging/metrics?
        # get_sem uses deterministic.deterministic_timestamp() if sandbox.
        # But here we are reading from Live DB.
        
        for i in range(4):
            for j in range(10):
                key = f"user/profile/user_{i}/item_{j}"
                res = semantic.get_sem(key)
                self.assertTrue(res["exists"], f"Key {key} missing")
                self.assertEqual(res["value"], f"value_{i}_{j}")

if __name__ == "__main__":
    unittest.main()
