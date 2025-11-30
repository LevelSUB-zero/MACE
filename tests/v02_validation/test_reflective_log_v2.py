import unittest
from mace.core import structures, deterministic

class TestReflectiveLogV2(unittest.TestCase):
    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")
        deterministic.init_seed("log_test_seed")

    def test_create_sem_snapshot(self):
        """Verify SEM snapshot creation."""
        key = "user/profile/test"
        value = {"foo": "bar"}
        read_seed = "read_seed_123"
        
        evidence = structures.create_sem_snapshot_evidence(key, value, read_seed)
        
        self.assertEqual(evidence["type"], "sem_read_snapshot")
        self.assertEqual(evidence["source"]["reference"], key)
        self.assertEqual(evidence["source"]["fetch_seed"], read_seed)
        self.assertEqual(evidence["content"]["structured"], value)
        self.assertIsNone(evidence["verifier"])
        self.assertIn("evidence_id", evidence)

    def test_max_evidence_size(self):
        """Verify MAX_EVIDENCE_SIZE handling."""
        key = "user/large_data"
        # Create large value > 16KB
        large_str = "x" * (16 * 1024 + 100)
        value = {"data": large_str}
        
        evidence = structures.create_sem_snapshot_evidence(key, value, "seed")
        
        self.assertIsNone(evidence["raw_payload"])
        self.assertIsNone(evidence["content"]["structured"])
        self.assertIn("Redacted", evidence["content"]["text"])
        self.assertTrue(len(evidence["provenance"]) > 0)
        self.assertIn("size limit", evidence["provenance"][0]["note"])

    def test_log_composition(self):
        """Verify ReflectiveLogEntry composition."""
        percept = structures.create_percept("test")
        decision = structures.create_router_decision(percept["percept_id"], [], "test", [], {})
        
        log = structures.create_reflective_log_entry(
            percept=percept,
            router_decision=decision,
            council_votes=[],
            final_output={"text": "done", "confidence": 1.0, "speculative": False},
            brainstate_before={},
            brainstate_after={},
            agent_outputs=[], # Added this
            evidence_items=[{"evidence_id": "ev1"}]
        )
        
        self.assertEqual(log["percept"]["percept_id"], percept["percept_id"])
        self.assertEqual(len(log["evidence_items"]), 1)
        self.assertIn("log_id", log)
        self.assertIn("timestamp", log)

if __name__ == '__main__':
    unittest.main()
