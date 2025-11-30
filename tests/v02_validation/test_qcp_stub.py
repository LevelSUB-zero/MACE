import unittest
from mace.core import qcp, deterministic

class TestQCPStub(unittest.TestCase):
    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")
        deterministic.init_seed("qcp_test_seed")

    def test_math_intent(self):
        """Verify math intent detection."""
        percept = {"text": "5 + 5"}
        snapshot = qcp.analyze_percept(percept)
        self.assertEqual(snapshot["intent_tags"], ["math_operation"])
        self.assertTrue(snapshot["features"]["math"])

    def test_profile_intent(self):
        """Verify profile intent detection."""
        percept = {"text": "My name is Alice"}
        snapshot = qcp.analyze_percept(percept)
        self.assertEqual(snapshot["intent_tags"], ["profile_update"])
        self.assertTrue(snapshot["features"]["profile"])

    def test_fact_intent(self):
        """Verify fact intent detection."""
        percept = {"text": "What is the capital of France?"}
        snapshot = qcp.analyze_percept(percept)
        self.assertEqual(snapshot["intent_tags"], ["knowledge_query"])
        self.assertTrue(snapshot["features"]["fact"])

    def test_general_intent(self):
        """Verify default intent."""
        percept = {"text": "Hello there"}
        snapshot = qcp.analyze_percept(percept)
        self.assertEqual(snapshot["intent_tags"], ["general_conversation"])

    def test_snapshot_structure(self):
        """Verify snapshot contains all required fields."""
        percept = {"text": "test"}
        snapshot = qcp.analyze_percept(percept)
        
        required_keys = ["intent_tags", "features", "depth_level", "urgency", "risk", "qcp_version", "random_seed"]
        for key in required_keys:
            self.assertIn(key, snapshot)
            
        self.assertEqual(snapshot["qcp_version"], "0.0.2-stub")
        self.assertEqual(snapshot["random_seed"], "qcp_test_seed")

if __name__ == '__main__':
    unittest.main()
