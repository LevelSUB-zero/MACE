"""
Stage-2 Phase 2.1 Tests: Event Instrumentation

Purpose: Verify event logging is frozen, deterministic, and replayable.
Spec: docs/stage2_ideology.md

Pass Criteria:
- Event types cannot be expanded
- Event IDs are deterministic
- Replay produces identical events
- Events are HMAC signed
"""

import unittest
import os
import sys
import sqlite3

# Set test DB path
DB_PATH = "stage2_test.db"
os.environ["MACE_DB_URL"] = f"sqlite:///{DB_PATH}"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

# Must import after setting DB path
import importlib
from mace.core import persistence, deterministic
importlib.reload(persistence)

from mace.stage2 import events


class TestEventSchemaFrozen(unittest.TestCase):
    """Test that event schema is frozen."""
    
    def test_event_types_exactly_six(self):
        """Verify exactly 6 event types."""
        self.assertEqual(len(events.EVENT_TYPES), 6)
    
    def test_event_types_content(self):
        """Verify event types are exactly as specified."""
        expected = [
            "wm_insert",
            "wm_expire",
            "episodic_write",
            "candidate_create",
            "council_vote",
            "amendment"
        ]
        self.assertEqual(events.EVENT_TYPES, expected)
    
    def test_invalid_event_type_rejected(self):
        """Verify invalid event types are rejected."""
        with self.assertRaises(ValueError):
            events._create_event(
                event_type="invalid_type",
                source_module="test",
                evidence_ids=[],
                payload={}
            )


class TestEventDeterminism(unittest.TestCase):
    """Test that events are deterministic."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.executescript("""
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
        """Reset deterministic seed before each test."""
        deterministic.init_seed("test_event_seed")
    
    def test_event_id_deterministic(self):
        """Verify event ID is deterministic for same inputs."""
        deterministic.init_seed("test_seed_1")
        event1 = events._create_event(
            event_type="wm_insert",
            source_module="test",
            evidence_ids=["ev1", "ev2"],
            payload={"test": "data"},
            job_seed="test_seed_1"
        )
        
        deterministic.init_seed("test_seed_1")
        event2 = events._create_event(
            event_type="wm_insert",
            source_module="test",
            evidence_ids=["ev1", "ev2"],
            payload={"test": "data"},
            job_seed="test_seed_1"
        )
        
        self.assertEqual(event1["event_id"], event2["event_id"])
    
    def test_different_inputs_different_ids(self):
        """Verify different inputs produce different event IDs."""
        deterministic.init_seed("test_seed_1")
        event1 = events._create_event(
            event_type="wm_insert",
            source_module="test",
            evidence_ids=["ev1"],
            payload={},
            job_seed="test_seed_1"
        )
        
        deterministic.init_seed("test_seed_1")
        event2 = events._create_event(
            event_type="wm_insert",
            source_module="test",
            evidence_ids=["ev2"],  # Different evidence
            payload={},
            job_seed="test_seed_1"
        )
        
        self.assertNotEqual(event1["event_id"], event2["event_id"])


class TestEventSigning(unittest.TestCase):
    """Test HMAC signing of events."""
    
    def setUp(self):
        deterministic.init_seed("signing_test_seed")
    
    def test_event_has_signature(self):
        """Verify signed events have signature fields."""
        event = events._create_event(
            event_type="council_vote",
            source_module="test",
            evidence_ids=[],
            payload={}
        )
        signed_event = events._sign_event(event)
        
        self.assertIn("signature", signed_event)
        self.assertIn("signature_key_id", signed_event)
    
    def test_signature_verifies(self):
        """Verify signature verification works."""
        event = events._create_event(
            event_type="amendment",
            source_module="test",
            evidence_ids=["cand_1"],
            payload={"reward": 1}
        )
        signed_event = events._sign_event(event)
        
        self.assertTrue(events.verify_event_signature(signed_event))
    
    def test_tampered_event_fails_verification(self):
        """Verify tampered events fail verification."""
        event = events._create_event(
            event_type="amendment",
            source_module="test",
            evidence_ids=["cand_1"],
            payload={}
        )
        signed_event = events._sign_event(event)
        
        # Tamper with the event
        signed_event["evidence_ids"] = ["tampered"]
        
        self.assertFalse(events.verify_event_signature(signed_event))


class TestEventLogging(unittest.TestCase):
    """Test event logging functions."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.executescript("""
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
        deterministic.init_seed("logging_test_seed")
    
    def test_log_wm_insert(self):
        """Verify WM insert event logging."""
        event_id = events.log_wm_insert(
            item_id="wm_123",
            content_summary="Test item",
            job_seed="wm_test"
        )
        self.assertIsNotNone(event_id)
    
    def test_log_episodic_write(self):
        """Verify episodic write event logging."""
        event_id = events.log_episodic_write(
            episodic_id="ep_456",
            summary="User said hello",
            job_seed="ep_test"
        )
        self.assertIsNotNone(event_id)
    
    def test_log_candidate_create(self):
        """Verify candidate create event logging."""
        event_id = events.log_candidate_create(
            candidate_id="cand_789",
            proposed_key="user/pref/color",
            features={"frequency": 3, "consistency": 0.9},
            job_seed="cand_test"
        )
        self.assertIsNotNone(event_id)
    
    def test_log_council_vote(self):
        """Verify council vote event logging."""
        event_id = events.log_council_vote(
            vote_id="vote_001",
            candidate_id="cand_789",
            labels={"truth": True, "safety": True},
            job_seed="vote_test"
        )
        self.assertIsNotNone(event_id)
    
    def test_log_amendment(self):
        """Verify amendment event logging."""
        event_id = events.log_amendment(
            amendment_id="amend_001",
            original_candidate_id="cand_789",
            delay_ticks=10,
            reward=-1,
            reason="correction",
            job_seed="amend_test"
        )
        self.assertIsNotNone(event_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
