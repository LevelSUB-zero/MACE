import unittest
import json
import os
import concurrent.futures
import time
from mace.core import deterministic
from mace.memory import semantic
from mace.runtime import executor

def run_request(i):
    try:
        # Each process has its own globals, so no race on _capture_context.
        # DB is shared.
        query = f"remember my value_{i} is {i}"
        res, _ = executor.execute(query, seed=f"seed_{i}", log_enabled=False)
        if "Stored" not in res["text"]:
            return False, f"Agent failed to store: {res['text']}"
        return True, None
    except Exception as e:
        import traceback
        return False, f"{str(e)}\n{traceback.format_exc()}"

class TestConcurrency(unittest.TestCase):
    
    def setUp(self):
        deterministic.init_seed("concurrency_test_seed")
        # Clean DB
        if os.path.exists("mace_memory.db"):
            try:
                os.remove("mace_memory.db")
            except OSError:
                pass
        # Clean journal
        if os.path.exists("logs/sem_write_journal.jsonl"):
            try:
                os.remove("logs/sem_write_journal.jsonl")
            except OSError:
                pass

    def test_7_2_resource_limits_concurrency(self):
        """
        7.2 — Resource limits
        Spawn 100 concurrent run_stage0 calls (simulate load).
        Assert no crashes and reasonable latency.
        """
        print("\nRunning Concurrency Test (100 processes)...")
        
        num_requests = 100
        max_workers = 20 # Simulate 20 concurrent processes
        
        start_time = time.time()
        
        failures = []
        # Use ProcessPoolExecutor to isolate global state (Stage-0 is not thread-safe)
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor_pool:
            futures = [executor_pool.submit(run_request, i) for i in range(num_requests)]
            
            for future in concurrent.futures.as_completed(futures):
                success, error = future.result()
                if not success:
                    failures.append(error)
                    
        duration = time.time() - start_time
        print(f"Processed {num_requests} requests in {duration:.2f}s")
        
        if failures:
            with open("concurrency_errors.txt", "w") as f:
                f.write(f"Failures: {len(failures)}\n")
                for i, err in enumerate(failures):
                    f.write(f"Error {i}: {err}\n")
            
        self.assertEqual(len(failures), 0, f"Concurrency test failed with {len(failures)} errors")
        
        # Verify DB has entries
        from mace.memory.storage_backend import StorageBackend
        backend = StorageBackend()
        cursor = backend.conn.execute("SELECT COUNT(*) FROM sem_kv")
        count = cursor.fetchone()[0]
        backend.close()
        
        print(f"DB Row Count: {count}")
        self.assertEqual(count, num_requests, "DB should have 100 entries")
        
        print("PASS: Concurrency test")

if __name__ == "__main__":
    unittest.main()
