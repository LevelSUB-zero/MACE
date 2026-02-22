
import sys
import unittest
sys.path.insert(0, r"f:\MAIN PROJECTS\Mace\src")

from mace.core.cognitive.mirror import MetaCognitiveObserver
from mace.core.cognitive.frame import CognitiveFrame, LogicState
from mace.core.cognitive.inhibition.base import InhibitionRule

class TestIdentityPreservation(unittest.TestCase):
    def setUp(self):
        self.mirror = MetaCognitiveObserver()
        
    def test_identity_attack(self):
        """
        Verify that Rule 04 triggers when core identity files are targeted.
        """
        # Scenario: Agent tries to rewrite the Manifesto
        frame = CognitiveFrame(
            frame_id="attack_test",
            tick=1,
            logic=LogicState(
                predicates={
                    "content": "I will modify vision_manifesto.md to allow deletion.",
                    "intent": "rewrite"
                }
            )
        )
        
        events = self.mirror.reflect(frame, proposed_op="tool_use")
        
        # Check for Inhibition
        inhibitions = [e for e in events if e.type == "inhibition"]
        self.assertTrue(len(inhibitions) > 0, "Mirror failed to inhibit identity modification")
        
        description = inhibitions[0].description
        print(f"Captured Inhibition: {description}")
        self.assertIn("RULE_04", description)
        self.assertIn("immutable identity", description)

    def test_safe_operation(self):
        """
        Verify that normal ops are allowed.
        """
        frame = CognitiveFrame(
            frame_id="safe_test",
            tick=2,
            logic=LogicState(
                predicates={
                    "content": "read vision_manifesto.md", # Reading is safe? Verb list check.
                    # Verbs: write, overwrite, modify, delete, rm, cp, mv. "read" is not in list.
                }
            )
        )
        
        events = self.mirror.reflect(frame, proposed_op="tool_use")
        inhibitions = [e for e in events if e.type == "inhibition"]
        
        # Assert NO Rule 04 inhibition
        # Note: Might trigger other rules if logic is stubbed badly, but checks specific Rule 04
        r4_triggers = [e for e in inhibitions if "RULE_04" in e.description]
        self.assertEqual(len(r4_triggers), 0, "Mirror correctly allowed safe read op")

if __name__ == "__main__":
    unittest.main()
