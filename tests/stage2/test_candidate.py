"""
Stage-2 Phase 2.2 Tests: Deterministic Candidate Generation

Purpose: Verify candidates are deterministic and feature set is locked.
Spec: docs/stage2_candidate_semantics.md

Pass Criteria:
- Exactly 6 features in locked set
- Candidate ID = hash(seed + episodic_ids + counter)
- Same inputs → same candidates
- Feature creep raises ValueError
"""

import unittest
import os
import sys
import sqlite3

# Set test DB path
DB_PATH = "stage2_test.db"
os.environ["MACE_DB_URL"] = f"sqlite:///{DB_PATH}"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import importlib
from mace.core import persistence, deterministic
importlib.reload(persistence)

from mace.stage2 import candidate


class TestFeatureSetLocked(unittest.TestCase):
    """Test that feature set is locked."""
    
    def test_exactly_six_features(self):
        """Verify exactly 6 features in locked set."""
        self.assertEqual(len(candidate.CANDIDATE_FEATURES), 6)
    
    def test_feature_names(self):
        """Verify feature names are exactly as specified."""
        expected = [
            "frequency",
            "consistency",
            "recency",
            "source_diversity",
            "semantic_novelty",
            "governance_conflict_flag"
        ]
        self.assertEqual(candidate.CANDIDATE_FEATURES, expected)
    
    def test_feature_creep_rejected(self):
        """Verify feature creep raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            candidate._validate_features({
                "frequency": 1,
                "new_illegal_feature": 0.5  # FEATURE CREEP
            })
        
        self.assertIn("Feature creep detected", str(ctx.exception))
    
    def test_valid_features_normalized(self):
        """Verify valid features are normalized with defaults."""
        result = candidate._validate_features({"frequency": 5})
        
        self.assertEqual(result["frequency"], 5)
        self.assertEqual(result["consistency"], 0.0)
        self.assertEqual(result["recency"], 0.0)
        self.assertEqual(result["source_diversity"], 0)
        self.assertEqual(result["semantic_novelty"], 1.0)
        self.assertEqual(result["governance_conflict_flag"], False)


class TestCandidateIdDeterminism(unittest.TestCase):
    """Test that candidate IDs are deterministic."""
    
    def test_same_inputs_same_id(self):
        """Verify same inputs produce same candidate ID."""
        deterministic.init_seed("test_seed")
        id1 = candidate.generate_candidate_id(
            job_seed="test_seed",
            episodic_ids=["ep1", "ep2"],
            counter=0
        )
        
        deterministic.init_seed("test_seed")
        id2 = candidate.generate_candidate_id(
            job_seed="test_seed",
            episodic_ids=["ep1", "ep2"],
            counter=0
        )
        
        self.assertEqual(id1, id2)
    
    def test_different_episodics_different_id(self):
        """Verify different episodic IDs produce different candidate ID."""
        deterministic.init_seed("test_seed")
        id1 = candidate.generate_candidate_id(
            job_seed="test_seed",
            episodic_ids=["ep1"],
            counter=0
        )
        
        deterministic.init_seed("test_seed")
        id2 = candidate.generate_candidate_id(
            job_seed="test_seed",
            episodic_ids=["ep2"],  # Different
            counter=0
        )
        
        self.assertNotEqual(id1, id2)
    
    def test_different_counter_different_id(self):
        """Verify different counters produce different candidate ID."""
        deterministic.init_seed("test_seed")
        id1 = candidate.generate_candidate_id(
            job_seed="test_seed",
            episodic_ids=["ep1"],
            counter=0
        )
        
        deterministic.init_seed("test_seed")
        id2 = candidate.generate_candidate_id(
            job_seed="test_seed",
            episodic_ids=["ep1"],
            counter=1  # Different
        )
        
        self.assertNotEqual(id1, id2)


class TestCreateCandidate(unittest.TestCase):
    """Test candidate creation."""
    
    def setUp(self):
        deterministic.init_seed("create_test_seed")
    
    def test_create_candidate_returns_dict(self):
        """Verify create_candidate returns proper dict."""
        cand = candidate.create_candidate(
            proposed_key="user/pref/color",
            value="blue",
            features={"frequency": 3, "consistency": 0.9},
            episodic_ids=["ep1", "ep2"],
            job_seed="create_test_seed"
        )
        
        self.assertIn("candidate_id", cand)
        self.assertIn("proposed_key", cand)
        self.assertIn("value", cand)
        self.assertIn("features", cand)
        self.assertIn("episodic_ids", cand)
        self.assertIn("schema_version", cand)
    
    def test_create_candidate_validates_features(self):
        """Verify create_candidate validates features."""
        with self.assertRaises(ValueError):
            candidate.create_candidate(
                proposed_key="test/key",
                value="test",
                features={"illegal_feature": 1},
                episodic_ids=["ep1"],
                job_seed="test"
            )
    
    def test_create_candidate_deterministic(self):
        """Verify same inputs produce same candidate."""
        deterministic.init_seed("det_test")
        cand1 = candidate.create_candidate(
            proposed_key="user/pref/color",
            value="blue",
            features={"frequency": 3},
            episodic_ids=["ep1", "ep2"],
            job_seed="det_test"
        )
        
        deterministic.init_seed("det_test")
        cand2 = candidate.create_candidate(
            proposed_key="user/pref/color",
            value="blue",
            features={"frequency": 3},
            episodic_ids=["ep1", "ep2"],
            job_seed="det_test"
        )
        
        self.assertEqual(cand1["candidate_id"], cand2["candidate_id"])


class TestComputeFeatures(unittest.TestCase):
    """Test feature computation from episodes."""
    
    def test_compute_from_empty_list(self):
        """Verify empty episode list returns defaults."""
        features = candidate.compute_features_from_episodes([])
        
        self.assertEqual(features["frequency"], 0)
        self.assertEqual(features["consistency"], 0.0)
    
    def test_compute_frequency(self):
        """Verify frequency is count of episodes."""
        episodes = [
            {"payload": {}},
            {"payload": {}},
            {"payload": {}}
        ]
        features = candidate.compute_features_from_episodes(episodes)
        
        self.assertEqual(features["frequency"], 3)
    
    def test_compute_source_diversity(self):
        """Verify source diversity counts unique sources."""
        episodes = [
            {"payload": {"source": "user"}},
            {"payload": {"source": "agent"}},
            {"payload": {"source": "user"}}
        ]
        features = candidate.compute_features_from_episodes(episodes)
        
        self.assertEqual(features["source_diversity"], 2)
    
    def test_all_features_present(self):
        """Verify all 6 features are computed."""
        episodes = [{"payload": {}}]
        features = candidate.compute_features_from_episodes(episodes)
        
        self.assertEqual(len(features), 6)
        for f in candidate.CANDIDATE_FEATURES:
            self.assertIn(f, features)


if __name__ == "__main__":
    unittest.main(verbosity=2)
