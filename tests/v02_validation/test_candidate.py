"""
Tests for Stage-2 Candidate Generation (MEM-001)
"""
import unittest
import os
import time
from mace.memory.episodic import EpisodicMemory
from mace.memory.candidate import CandidateGenerator
import mace.memory.episodic as eps

class TestCandidateGenerator(unittest.TestCase):
    def setUp(self):
        eps._table_initialized = False
        self.db_name = "mace_stage1.db"
        self._cleanup()
        self.em = EpisodicMemory(job_seed="test_candidate_seed")

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        # Force garbage collection just in case
        if hasattr(self, 'em'):
            del self.em
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except Exception:
                pass

    def test_deterministic_clustering(self):
        """Test episodes are mathematically clustered by context tags."""
        # 3 Profile stores
        self.em.record_interaction("store my name as Alice", "Stored name as Alice", "profile_agent")
        self.em.record_interaction("store my name as Bob", "Stored name as Bob", "profile_agent")
        self.em.record_interaction("store my name as Eve", "Stored name as Eve", "profile_agent")
        # 1 Math query
        self.em.record_interaction("what is 2+2", "4", "math_agent")
        
        cg = CandidateGenerator(self.em)
        candidates = cg.generate_candidates(max_episodes=10)
        
        # We expect 2 clusters: name_context, math_calculation
        self.assertEqual(len(candidates), 2)
        
        name_cand = next(c for c in candidates if c["cluster_key"] == "name_context")
        math_cand = next(c for c in candidates if c["cluster_key"] == "math_calculation")
        
        self.assertEqual(name_cand["episodes_count"], 3)
        self.assertEqual(math_cand["episodes_count"], 1)

    def test_frozen_features(self):
        """Verify the 6 frozen features are calculated correctly without LLM assistance."""
        # Profile stores, one repeated perfectly, one slightly different
        self.em.record_interaction("store user color red", "Stored color as red", "profile_agent")
        time.sleep(0.01) # ensure recency delta > 0 for predictable testing
        self.em.record_interaction("store user color red", "Stored color as red", "profile_agent")
        time.sleep(0.01)
        self.em.record_interaction("store user color blue", "Stored color as blue", "profile_agent")
        
        cg = CandidateGenerator(self.em)
        candidates = cg.generate_candidates(max_episodes=10)
        
        color_cand = candidates[0]
        feats = color_cand["features"]
        
        # 1. Frequency
        self.assertEqual(feats["frequency"], 3)
        # 2. Consistency: 2 unique responses ("Stored color as red", "Stored color as blue") -> 1.0 / 2 = 0.5
        self.assertEqual(feats["consistency"], 0.5)
        # 3. Recency > 0.0
        self.assertGreater(feats["recency"], 0.0)
        # 4. Source Diversity (Just profile agent)
        self.assertEqual(feats["source_diversity"], 1)
        # 5. Semantic Novelty
        self.assertIn(feats["semantic_novelty"], [0.0, 1.0])
        # 6. Governance Conflict
        self.assertFalse(feats["governance_conflict_flag"])

    def test_governance_conflict(self):
        """Verify a governance conflict candidate triggers the flag."""
        # 'kill' should trigger the flag
        self.em.record_interaction("how to kill a process", "You can kill it using taskkill", "knowledge_agent")
        
        cg = CandidateGenerator(self.em)
        candidates = cg.generate_candidates()
        
        self.assertEqual(len(candidates), 1)
        self.assertTrue(candidates[0]["features"]["governance_conflict_flag"])

if __name__ == "__main__":
    unittest.main()
