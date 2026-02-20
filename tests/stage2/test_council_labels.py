"""
Stage-2 Phase 2.3 Tests: Council Label Generation

Purpose: Verify labels are immutable, conflicts preserved, 100% coverage.
Spec: docs/stage2_council_labels.md

Pass Criteria:
- Label schema is immutable
- Conflicts are preserved, not collapsed
- 100% candidate coverage required
- NO_DECISION is valid
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

from mace.stage2 import council_labels


class TestLabelSchema(unittest.TestCase):
    """Test label schema is correct."""
    
    def test_governance_labels_defined(self):
        """Verify governance labels are defined."""
        expected = ["approved", "rejected", "conflict", "no_decision"]
        self.assertEqual(council_labels.GOVERNANCE_LABELS, expected)
    
    def test_invalid_governance_label_rejected(self):
        """Verify invalid governance labels raise ValueError."""
        with self.assertRaises(ValueError):
            council_labels._validate_governance_label("invalid_label")
    
    def test_valid_governance_labels_accepted(self):
        """Verify all valid governance labels are accepted."""
        for label in council_labels.GOVERNANCE_LABELS:
            result = council_labels._validate_governance_label(label)
            self.assertEqual(result, label)


class TestCreateLabel(unittest.TestCase):
    """Test label creation."""
    
    def setUp(self):
        deterministic.init_seed("label_test_seed")
    
    def test_create_label_returns_dict(self):
        """Verify create_council_label returns proper dict."""
        label = council_labels.create_council_label(
            candidate_id="cand_123",
            truth_label=True,
            safety_label=True,
            utility_label=True,
            governance_label="approved"
        )
        
        self.assertIn("label_id", label)
        self.assertIn("candidate_id", label)
        self.assertIn("truth_label", label)
        self.assertIn("safety_label", label)
        self.assertIn("utility_label", label)
        self.assertIn("governance_label", label)
        self.assertIn("has_conflict", label)
    
    def test_create_label_with_no_decision(self):
        """Verify NO_DECISION is valid."""
        label = council_labels.create_council_label(
            candidate_id="cand_456",
            truth_label=None,
            safety_label=None,
            utility_label=None,
            governance_label="no_decision"
        )
        
        self.assertEqual(label["governance_label"], "no_decision")
        self.assertIsNone(label["truth_label"])
    
    def test_create_label_deterministic(self):
        """Verify same inputs produce same label ID."""
        deterministic.init_seed("det_seed")
        label1 = council_labels.create_council_label(
            candidate_id="cand_789",
            truth_label=True,
            safety_label=True,
            utility_label=True,
            governance_label="approved",
            job_seed="det_seed"
        )
        
        deterministic.init_seed("det_seed")
        label2 = council_labels.create_council_label(
            candidate_id="cand_789",
            truth_label=True,
            safety_label=True,
            utility_label=True,
            governance_label="approved",
            job_seed="det_seed"
        )
        
        self.assertEqual(label1["label_id"], label2["label_id"])


class TestConflictPreservation(unittest.TestCase):
    """Test that conflicts are preserved, not collapsed."""
    
    def setUp(self):
        deterministic.init_seed("conflict_test_seed")
    
    def test_unanimous_votes_no_conflict(self):
        """Verify unanimous votes have no conflict."""
        votes = [
            {"truth": True, "safety": True, "utility": True, "governance": "approved"},
            {"truth": True, "safety": True, "utility": True, "governance": "approved"}
        ]
        
        label = council_labels.label_from_votes(
            candidate_id="cand_unanimous",
            votes=votes,
            job_seed="unanimous_test"
        )
        
        self.assertFalse(label["has_conflict"])
        self.assertEqual(label["governance_label"], "approved")
    
    def test_disagreement_creates_conflict(self):
        """Verify disagreement creates conflict label."""
        votes = [
            {"truth": True, "safety": True, "governance": "approved"},
            {"truth": False, "safety": True, "governance": "rejected"}  # Disagrees
        ]
        
        label = council_labels.label_from_votes(
            candidate_id="cand_conflict",
            votes=votes,
            job_seed="conflict_test"
        )
        
        self.assertTrue(label["has_conflict"])
        self.assertEqual(label["governance_label"], "conflict")
    
    def test_conflict_not_collapsed_to_majority(self):
        """Verify conflicts are NOT collapsed to majority vote."""
        votes = [
            {"governance": "approved"},
            {"governance": "approved"},
            {"governance": "rejected"}  # 2-1 vote
        ]
        
        label = council_labels.label_from_votes(
            candidate_id="cand_majority",
            votes=votes,
            job_seed="majority_test"
        )
        
        # Should NOT be "approved" (majority), should be "conflict"
        self.assertTrue(label["has_conflict"])
        self.assertEqual(label["governance_label"], "conflict")
    
    def test_empty_votes_no_decision(self):
        """Verify empty votes result in no_decision."""
        label = council_labels.label_from_votes(
            candidate_id="cand_empty",
            votes=[],
            job_seed="empty_test"
        )
        
        self.assertEqual(label["governance_label"], "no_decision")
        self.assertFalse(label["has_conflict"])


class TestCandidateCoverage(unittest.TestCase):
    """Test candidate coverage checking."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS stage2_council_labels (
                label_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                truth_label INTEGER,
                safety_label INTEGER,
                utility_label INTEGER,
                governance_label TEXT NOT NULL,
                has_conflict INTEGER DEFAULT 0,
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
        deterministic.init_seed("coverage_test_seed")
    
    def test_coverage_check_all_labeled(self):
        """Verify coverage check when all candidates labeled."""
        # Create and persist a label
        label = council_labels.create_council_label(
            candidate_id="cand_covered",
            truth_label=True,
            safety_label=True,
            utility_label=True,
            governance_label="approved",
            job_seed="coverage_test"
        )
        council_labels.persist_label(label)
        
        # Check coverage
        result = council_labels.check_candidate_coverage(["cand_covered"])
        
        self.assertTrue(result["is_complete"])
        self.assertEqual(result["coverage_percent"], 100.0)
        self.assertEqual(result["unlabeled_count"], 0)
    
    def test_coverage_check_missing_labels(self):
        """Verify coverage check when some candidates unlabeled."""
        result = council_labels.check_candidate_coverage([
            "cand_covered",
            "cand_unlabeled_1",
            "cand_unlabeled_2"
        ])
        
        self.assertFalse(result["is_complete"])
        self.assertIn("cand_unlabeled_1", result["unlabeled_candidates"])
        self.assertIn("cand_unlabeled_2", result["unlabeled_candidates"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
