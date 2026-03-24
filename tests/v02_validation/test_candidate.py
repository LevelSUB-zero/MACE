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
        
        # Verify we get clusters (exact count depends on tag inference + KG tags)
        self.assertGreater(len(candidates), 0, "No candidates generated")
        
        # Verify math cluster exists
        cluster_keys = [c["cluster_key"] for c in candidates]
        self.assertTrue(
            any("math" in k for k in cluster_keys),
            f"No math cluster found in {cluster_keys}"
        )
        
        # Verify name-related cluster exists  
        self.assertTrue(
            any("name" in k for k in cluster_keys),
            f"No name cluster found in {cluster_keys}"
        )

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
        
        # Find the color-related cluster
        color_cand = None
        for c in candidates:
            if "color" in c["cluster_key"]:
                color_cand = c
                break
        
        self.assertIsNotNone(color_cand, f"No color cluster found. Got: {[c['cluster_key'] for c in candidates]}")
        feats = color_cand["features"]
        
        # 1. Frequency - at least the color-tagged episodes
        self.assertGreater(feats["frequency"], 0)
        # 2. Consistency: ratio based on unique responses
        self.assertGreater(feats["consistency"], 0.0)
        self.assertLessEqual(feats["consistency"], 1.0)
        # 3. Recency > 0.0
        self.assertGreaterEqual(feats["recency"], 0.0)
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
        
        # Find any candidate with governance conflict
        self.assertGreater(len(candidates), 0, "No candidates generated")
        conflict_candidates = [c for c in candidates if c["features"]["governance_conflict_flag"]]
        self.assertGreater(len(conflict_candidates), 0, "No governance conflict detected")

if __name__ == "__main__":
    unittest.main()
