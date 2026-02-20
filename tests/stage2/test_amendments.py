"""
Stage-2 Phase 2.4 Tests: Amendments (Delayed Rewards)

Purpose: Verify amendments are append-only with explicit backward linkage.
Spec: docs/stage2_amendments.md

Pass Criteria:
- Amendments are append-only
- Backward linkage is explicit
- No silent reward inference
- Invalid triggers rejected
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

from mace.stage2 import amendments


class TestAmendmentSchema(unittest.TestCase):
    """Test amendment schema is correct."""
    
    def test_amendment_reasons_defined(self):
        """Verify amendment reasons are defined."""
        expected = ["correction", "contradiction", "confirmation"]
        self.assertEqual(amendments.AMENDMENT_REASONS, expected)
    
    def test_invalid_reason_rejected(self):
        """Verify invalid reasons raise ValueError."""
        with self.assertRaises(ValueError):
            amendments._validate_reason("invalid_reason")
    
    def test_valid_reasons_accepted(self):
        """Verify all valid reasons are accepted."""
        for reason in amendments.AMENDMENT_REASONS:
            result = amendments._validate_reason(reason)
            self.assertEqual(result, reason)
    
    def test_invalid_reward_rejected(self):
        """Verify invalid rewards raise ValueError."""
        with self.assertRaises(ValueError):
            amendments._validate_reward(0)  # Must be -1 or +1
        
        with self.assertRaises(ValueError):
            amendments._validate_reward(2)
    
    def test_valid_rewards_accepted(self):
        """Verify valid rewards are accepted."""
        self.assertEqual(amendments._validate_reward(-1), -1)
        self.assertEqual(amendments._validate_reward(1), 1)


class TestCreateAmendment(unittest.TestCase):
    """Test amendment creation."""
    
    def setUp(self):
        deterministic.init_seed("amendment_test_seed")
    
    def test_create_amendment_returns_dict(self):
        """Verify create_amendment returns proper dict."""
        amend = amendments.create_amendment(
            original_candidate_id="cand_123",
            delay_ticks=10,
            reward=-1,
            reason="correction"
        )
        
        self.assertIn("amendment_id", amend)
        self.assertIn("original_candidate_id", amend)
        self.assertIn("delay_ticks", amend)
        self.assertIn("reward", amend)
        self.assertIn("reason", amend)
    
    def test_create_amendment_deterministic(self):
        """Verify same inputs produce same amendment ID."""
        deterministic.init_seed("det_seed")
        amend1 = amendments.create_amendment(
            original_candidate_id="cand_789",
            delay_ticks=5,
            reward=1,
            reason="confirmation",
            job_seed="det_seed"
        )
        
        deterministic.init_seed("det_seed")
        amend2 = amendments.create_amendment(
            original_candidate_id="cand_789",
            delay_ticks=5,
            reward=1,
            reason="confirmation",
            job_seed="det_seed"
        )
        
        self.assertEqual(amend1["amendment_id"], amend2["amendment_id"])


class TestInvalidTriggers(unittest.TestCase):
    """Test that invalid triggers are rejected."""
    
    def test_overwrite_not_valid_trigger(self):
        """Verify overwrite is not a valid amendment trigger."""
        self.assertFalse(amendments.is_valid_amendment_trigger("overwrite"))
    
    def test_decay_not_valid_trigger(self):
        """Verify decay is not a valid amendment trigger."""
        self.assertFalse(amendments.is_valid_amendment_trigger("decay"))
    
    def test_replacement_not_valid_trigger(self):
        """Verify replacement is not a valid amendment trigger."""
        self.assertFalse(amendments.is_valid_amendment_trigger("replacement"))
    
    def test_silence_not_valid_trigger(self):
        """Verify silence is not a valid amendment trigger."""
        self.assertFalse(amendments.is_valid_amendment_trigger("silence"))
    
    def test_explicit_correction_is_valid(self):
        """Verify explicit correction is a valid trigger."""
        self.assertTrue(amendments.is_valid_amendment_trigger("user_correction"))
        self.assertTrue(amendments.is_valid_amendment_trigger("evidence_update"))


class TestBackwardLinkage(unittest.TestCase):
    """Test backward linkage validation."""
    
    def test_missing_candidate_id_fails(self):
        """Verify missing candidate ID fails validation."""
        amend = {"delay_ticks": 5, "reward": -1, "reason": "correction"}
        result = amendments.validate_backward_linkage(amend)
        
        self.assertFalse(result["valid"])
        self.assertTrue(any("backward linkage" in issue.lower() for issue in result["issues"]))
    
    def test_negative_delay_fails(self):
        """Verify negative delay_ticks fails validation."""
        amend = {
            "original_candidate_id": "cand_123",
            "delay_ticks": -5,
            "reward": -1,
            "reason": "correction"
        }
        result = amendments.validate_backward_linkage(amend)
        
        self.assertFalse(result["valid"])
    
    def test_valid_linkage_passes(self):
        """Verify valid backward linkage passes validation."""
        amend = {
            "original_candidate_id": "cand_123",
            "delay_ticks": 10,
            "reward": 1,
            "reason": "confirmation"
        }
        result = amendments.validate_backward_linkage(amend)
        
        self.assertTrue(result["valid"])


class TestAmendmentPersistence(unittest.TestCase):
    """Test amendment persistence."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS stage2_amendments (
                amendment_id TEXT PRIMARY KEY,
                original_candidate_id TEXT NOT NULL,
                delay_ticks INTEGER NOT NULL,
                reward INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS stage2_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                source_module TEXT NOT NULL,
                event_json TEXT NOT NULL,
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
        deterministic.init_seed("persist_test_seed")
    
    def test_persist_and_retrieve(self):
        """Verify persist and retrieve works."""
        amend = amendments.create_amendment(
            original_candidate_id="cand_persist_test",
            delay_ticks=10,
            reward=-1,
            reason="correction",
            job_seed="persist_test"
        )
        
        amendments.persist_amendment(amend)
        
        retrieved = amendments.get_amendments_for_candidate("cand_persist_test")
        
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0]["original_candidate_id"], "cand_persist_test")
        self.assertEqual(retrieved[0]["reward"], -1)
    
    def test_cumulative_reward(self):
        """Verify cumulative reward computation."""
        # Create multiple amendments for same candidate
        deterministic.init_seed("cumulative_seed_1")
        amend1 = amendments.create_amendment(
            original_candidate_id="cand_cumulative",
            delay_ticks=5,
            reward=-1,
            reason="correction",
            job_seed="cumulative_seed_1"
        )
        amendments.persist_amendment(amend1)
        
        deterministic.init_seed("cumulative_seed_2")
        amend2 = amendments.create_amendment(
            original_candidate_id="cand_cumulative",
            delay_ticks=10,
            reward=1,
            reason="confirmation",
            job_seed="cumulative_seed_2"
        )
        amendments.persist_amendment(amend2)
        
        total = amendments.compute_cumulative_reward("cand_cumulative")
        
        self.assertEqual(total, 0)  # -1 + 1 = 0


if __name__ == "__main__":
    unittest.main(verbosity=2)
