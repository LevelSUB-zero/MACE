import unittest
import os
import time
from mace.runtime import executor
from mace.core import deterministic, replay
from mace.memory import semantic

class TestGoldenStage0(unittest.TestCase):
    
    def setUp(self):
        # Reset DB for tests
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")
        if os.path.exists("logs/sem_write_journal.jsonl"):
            os.remove("logs/sem_write_journal.jsonl")
        if os.path.exists("logs/reflective_log.jsonl"):
            os.remove("logs/reflective_log.jsonl")
            
        # Reset seed
        deterministic.init_seed("golden_test_seed")

    def test_G1_favorite_color_recall(self):
        print("\n=== Test G1: Favorite Color Recall ===")
        
        # 1. Write
        write_res, _ = executor.execute("remember my favorite_color is blue")
        self.assertIn("Stored favorite_color = blue", write_res["text"])
        
        # 2. Query
        query_res, log_entry = executor.execute("what is my favorite_color")
        self.assertIn("blue", query_res["text"])
        self.assertEqual(query_res["confidence"], 1.0)
        
        # 3. Replay
        print("Running Replay for G1 Query...")
        replay.replay_log(log_entry)
        print("Replay G1 Passed.")

    def test_G2_last_write_wins(self):
        print("\n=== Test G2: Last Write Wins ===")
        
        # t1: Green
        executor.execute("remember my favorite_color is green")
        # Sleep to ensure timestamp diff? 
        # Deterministic timestamp depends on counter, so order matters, not wall time.
        
        # t2: Red
        executor.execute("remember my favorite_color is red")
        
        # Query
        query_res, log_entry = executor.execute("what is my favorite_color")
        self.assertIn("red", query_res["text"])
        self.assertNotIn("green", query_res["text"])
        
        # Replay
        print("Running Replay for G2 Query...")
        replay.replay_log(log_entry)
        print("Replay G2 Passed.")

    def test_G3_router_fallback(self):
        print("\n=== Test G3: Router Fallback ===")
        
        # Setup: We need to force math_agent to fail.
        # We can monkeypatch it.
        from mace.agents import math_agent
        original_run = math_agent.run
        
        def fail_run(percept):
            raise RuntimeError("Forced Crash")
            
        math_agent.run = fail_run
        
        try:
            # Query
            query_res, log_entry = executor.execute("2 + 2")
            
            # Check Fallback
            self.assertIn("One of my internal modules failed", query_res["text"])
            self.assertEqual(query_res["confidence"], 0.0)
            
            # Check Log has Error
            self.assertTrue(len(log_entry["errors"]) > 0)
            self.assertIn("Forced Crash", log_entry["errors"][0]["message"])
            
            # Replay
            # Note: Replay must also fail! So we keep the monkeypatch active.
            print("Running Replay for G3 Query...")
            replay.replay_log(log_entry)
            print("Replay G3 Passed.")
            
        finally:
            # Restore
            math_agent.run = original_run

    def test_G4_sem_only(self):
        print("\n=== Test G4: SEM Only ===")
        
        # Query about past
        query_res, log_entry = executor.execute("what did I say 5 minutes ago")
        
        # Expected: Generic agent fallback or "I don't have enough info"
        # Since "what did I say" doesn't match R1, R2, R3 (R3 is "what is", "define" etc. - "what did" might match "what is" prefix? No.)
        # R3 regex: ^(what is|define|who is|when was|where is)
        # "what did" does NOT match.
        # So R4 Fallback -> Generic Agent.
        
        self.assertIn("I don’t have enough stored info to answer that yet", query_res["text"])
        
        # Replay
        print("Running Replay for G4 Query...")
        replay.replay_log(log_entry)
        print("Replay G4 Passed.")

if __name__ == "__main__":
    unittest.main()
