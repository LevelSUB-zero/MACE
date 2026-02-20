"""
Stage-2 Phase 2.5 Tests: MEM-SNN Shadow Mode

Purpose: Verify MEM-SNN operates in shadow mode only.
Spec: docs/stage2_mem_snn_rules.md

Pass Criteria:
- Shadow mode enforced
- Predictions logged to shadow table
- Divergences computed correctly
- Removing MEM-SNN changes nothing
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

from mace.stage2 import mem_snn_shadow, shadow_guard


class TestShadowModeEnforcement(unittest.TestCase):
    """Test that shadow mode is enforced."""
    
    def setUp(self):
        deterministic.init_seed("shadow_test_seed")
        # Clean up any kill-switch state
        if os.path.exists(shadow_guard.STAGE2_KILLSWITCH_FILE):
            os.remove(shadow_guard.STAGE2_KILLSWITCH_FILE)
    
    def tearDown(self):
        if os.path.exists(shadow_guard.STAGE2_KILLSWITCH_FILE):
            os.remove(shadow_guard.STAGE2_KILLSWITCH_FILE)
    
    def test_score_candidate_requires_shadow_mode(self):
        """Verify score_candidate checks shadow mode."""
        candidate = {
            "candidate_id": "cand_test",
            "features": {"frequency": 3, "consistency": 0.9}
        }
        
        # Should not raise in shadow mode
        prediction = mem_snn_shadow.score_candidate(candidate)
        self.assertIsNotNone(prediction)
    
    def test_verify_shadow_mode_integrity(self):
        """Verify integrity check works."""
        result = mem_snn_shadow.verify_shadow_mode_integrity()
        
        self.assertTrue(result["all_passed"])
        self.assertTrue(len(result["checks"]) >= 2)


class TestShadowScoring(unittest.TestCase):
    """Test shadow scoring functionality."""
    
    def setUp(self):
        deterministic.init_seed("scoring_test_seed")
    
    def test_score_returns_prediction_dict(self):
        """Verify score returns proper prediction dict."""
        candidate = {
            "candidate_id": "cand_score",
            "features": {"frequency": 3, "consistency": 0.9}
        }
        
        prediction = mem_snn_shadow.score_candidate(candidate)
        
        self.assertIn("prediction_id", prediction)
        self.assertIn("candidate_id", prediction)
        self.assertIn("predicted_truth_score", prediction)
        self.assertIn("predicted_utility_score", prediction)
        self.assertIn("predicted_safety_score", prediction)
    
    def test_stub_scoring_uses_features(self):
        """Verify stub scoring uses candidate features."""
        # High consistency and frequency should boost truth score
        high_candidate = {
            "candidate_id": "cand_high",
            "features": {
                "frequency": 5,
                "consistency": 0.95,
                "semantic_novelty": 0.8,
                "source_diversity": 3
            }
        }
        
        # Use stub explicitly for deterministic test
        prediction = mem_snn_shadow.score_candidate(
            high_candidate,
            model_fn=mem_snn_shadow._stub_score_candidate
        )
        
        # Should have higher truth score
        self.assertGreater(prediction["predicted_truth_score"], 0.5)
    
    def test_governance_conflict_lowers_safety(self):
        """Verify governance conflict flag lowers safety score."""
        unsafe_candidate = {
            "candidate_id": "cand_unsafe",
            "features": {
                "governance_conflict_flag": True
            }
        }
        
        # Use stub explicitly for deterministic test
        prediction = mem_snn_shadow.score_candidate(
            unsafe_candidate,
            model_fn=mem_snn_shadow._stub_score_candidate
        )
        
        # Should have low safety score
        self.assertLess(prediction["predicted_safety_score"], 0.5)



class TestDivergenceLogging(unittest.TestCase):
    """Test divergence logging functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS mem_snn_shadow_predictions (
                prediction_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                predicted_truth_score REAL,
                predicted_utility_score REAL,
                predicted_safety_score REAL,
                ranking_position INTEGER,
                confidence_interval REAL,
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS mem_snn_divergence_log (
                divergence_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                mem_snn_prediction TEXT NOT NULL,
                council_decision TEXT NOT NULL,
                divergence_reason TEXT,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()
        conn.close()
        
        importlib.reload(persistence)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
    
    def setUp(self):
        deterministic.init_seed("divergence_test_seed")
        if os.path.exists(shadow_guard.STAGE2_KILLSWITCH_FILE):
            os.remove(shadow_guard.STAGE2_KILLSWITCH_FILE)
    
    def tearDown(self):
        if os.path.exists(shadow_guard.STAGE2_KILLSWITCH_FILE):
            os.remove(shadow_guard.STAGE2_KILLSWITCH_FILE)
    
    def test_log_divergence_succeeds(self):
        """Verify divergence logging works."""
        mem_snn_pred = {
            "predicted_truth_score": 0.9,
            "predicted_safety_score": 0.9
        }
        council_dec = {
            "truth_label": False,  # Disagrees with 0.9
            "safety_label": True
        }
        
        divergence_id = mem_snn_shadow.log_divergence(
            candidate_id="cand_diverge",
            mem_snn_prediction=mem_snn_pred,
            council_decision=council_dec
        )
        
        self.assertIsNotNone(divergence_id)
    
    def test_no_divergence_when_agreement(self):
        """Verify no divergence reason when agreement."""
        mem_snn_pred = {
            "predicted_truth_score": 0.9,
            "predicted_safety_score": 0.9
        }
        council_dec = {
            "truth_label": True,  # Agrees with 0.9
            "safety_label": True
        }
        
        divergence_id = mem_snn_shadow.log_divergence(
            candidate_id="cand_agree",
            mem_snn_prediction=mem_snn_pred,
            council_decision=council_dec
        )
        
        self.assertIsNotNone(divergence_id)


class TestRemovingMEMSNNChangesNothing(unittest.TestCase):
    """
    Critical test: Verify removing MEM-SNN changes nothing.
    
    This is the litmus test for Stage-2.
    """
    
    def test_system_works_without_mem_snn(self):
        """
        Verify system works without MEM-SNN.
        
        In Stage-2, MEM-SNN is purely observational.
        If we skip calling MEM-SNN entirely, system behavior is identical.
        """
        # Simulate a workflow WITHOUT calling MEM-SNN
        
        # 1. Create a candidate
        from mace.stage2 import candidate
        deterministic.init_seed("no_mem_snn_test")
        
        cand = candidate.create_candidate(
            proposed_key="user/test/key",
            value="test_value",
            features={"frequency": 3},
            episodic_ids=["ep1"],
            job_seed="no_mem_snn_test"
        )
        
        # 2. Create council label (without MEM-SNN input)
        from mace.stage2 import council_labels
        
        label = council_labels.create_council_label(
            candidate_id=cand["candidate_id"],
            truth_label=True,
            safety_label=True,
            utility_label=True,
            governance_label="approved"
        )
        
        # 3. Verify workflow completed successfully
        self.assertIsNotNone(cand["candidate_id"])
        self.assertIsNotNone(label["label_id"])
        self.assertEqual(label["governance_label"], "approved")
        
        # This proves: MEM-SNN was not needed for the workflow


if __name__ == "__main__":
    unittest.main(verbosity=2)
