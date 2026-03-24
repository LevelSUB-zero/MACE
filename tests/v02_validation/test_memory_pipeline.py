"""
tests/v02_validation/test_memory_pipeline.py
End-to-End Memory Pipeline Test for Stage-2.
Validates:
1. Executor runs (producing WM/Episodic).
2. Episodic saves correctly using job_seed.
3. CandidateGenerator extracts identical requests into a hypothesis cluster.
"""
import unittest
import os
import time
from mace.runtime import executor
from mace.core import deterministic
from mace.memory.episodic import EpisodicMemory
from mace.memory.candidate import CandidateGenerator

class TestMemoryPipelineE2E(unittest.TestCase):
    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")
        self.job_seed = "e2e_pipeline_seed"
        deterministic.init_seed(self.job_seed)
        
        # Reset globals for testing
        from mace.reflective import writer
        from mace.brainstate import persistence as bs_persistence
        from mace.memory import semantic
        import mace.memory.episodic as eps
        
        writer._table_initialized = False
        bs_persistence._table_initialized = False
        semantic._tables_initialized = False
        eps._table_initialized = False
        
        self.db_stage1 = "mace_stage1.db"
        self.db_memory = "mace_memory.db"
        self._cleanup()

    def tearDown(self):
        self._cleanup()
        
    def _cleanup(self):
        if hasattr(self, 'em'):
            del self.em
        if os.path.exists(self.db_stage1):
            try:
                os.remove(self.db_stage1)
            except Exception:
                pass
        if os.path.exists(self.db_memory):
            try:
                os.remove(self.db_memory)
            except Exception:
                pass
        if os.path.exists("logs/reflective_log.jsonl"):
            try:
                os.remove("logs/reflective_log.jsonl")
            except Exception:
                pass
        if os.path.exists("logs/sem_write_journal.jsonl"):
            try:
                os.remove("logs/sem_write_journal.jsonl")
            except Exception:
                pass

    def test_end_to_end_candidate_extraction(self):
        """
        Verify that multiple calls to the executor gracefully populate episodic memory,
        and the CandidateGenerator successfully clusters them into hypotheses.
        """
        # Use slightly varying math questions so they produce unique reflective logs
        # but all map to the math_agent to test candidate consistency grouping.
        executor.execute("what is 4+4", seed=self.job_seed)
        time.sleep(0.01)
        executor.execute("what is 4 + 4", seed=self.job_seed)
        time.sleep(0.01)
        executor.execute("calculate 4+4", seed=self.job_seed)
        
        # Verify memory pipeline
        self.em = EpisodicMemory(job_seed=self.job_seed)
        recent_eps = self.em.get_recent(n=10)
        
        self.assertGreaterEqual(len(recent_eps), 3, "Executor failed to write to Episodic memory.")
        
        # Generate candidates
        cg = CandidateGenerator(self.em)
        candidates = cg.generate_candidates(max_episodes=10)
        
        # We expect a cluster for math
        math_cand = next((c for c in candidates if c["cluster_key"] == "math_calculation"), None)
        self.assertIsNotNone(math_cand, "Candidate clustering failed to identify 'math_calculation'.")
        
        # Ensure the mathematically clustered features are robust
        feats = math_cand["features"]
        self.assertGreaterEqual(feats["frequency"], 3)
        self.assertGreater(feats["consistency"], 0.0, "Consistency should be positive.")
        self.assertLessEqual(feats["consistency"], 1.0, "Consistency should be <= 1.0.")
        self.assertEqual(feats["source_diversity"], 1, "Expected only math_agent.")
        self.assertFalse(feats["governance_conflict_flag"])

if __name__ == "__main__":
    unittest.main()
