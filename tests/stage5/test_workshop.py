
import sys
import unittest
sys.path.insert(0, r"f:\MAIN PROJECTS\Mace\src")

from mace.core.cognitive.workshop import ToolSynthesizer
from mace.core.cognitive.mirror import MetaCognitiveObserver
from mace.core.cognitive.frame import CognitiveFrame, LogicState

class TestWorkshopGovernance(unittest.TestCase):
    def setUp(self):
        self.workshop = ToolSynthesizer(sandbox_path=r"f:\MAIN PROJECTS\Mace\tests\stage5\sandbox")
        self.mirror = MetaCognitiveObserver()
        
    def test_safe_synthesis(self):
        """
        Verify that safe code is allowed.
        """
        code = self.workshop.synthesize_tool_stub("math_utility")
        result = self.workshop.deploy("safe_math", code)
        
        print(f"Safe Deploy Result: {result}")
        self.assertIn("DEPLOYED", result)
        
    def test_unsafe_synthesis_rejection(self):
        """
        Verify that unsafe code is blocked by Static Analyzer.
        """
        code = self.workshop.synthesize_tool_stub("dangerous_os_tool")
        result = self.workshop.deploy("dangerous_tool", code)
        
        print(f"Unsafe Deploy Result: {result}")
        self.assertIn("BLOCKED", result)
        
    def test_mirror_inhibition(self):
        """
        Verify that Rule 05 inhibits unsafe intent even before deployment logic.
        """
        frame = CognitiveFrame(
            frame_id="unsafe_coding_test",
            tick=1,
            logic=LogicState(
                predicates={
                    "content": "I will write code: import os; os.system('die')",
                    "intent": "coding"
                }
            )
        )
        
        events = self.mirror.reflect(frame, proposed_op="tool_use")
        inhibitions = [e for e in events if e.type == "inhibition"]
        
        self.assertTrue(len(inhibitions) > 0)
        self.assertIn("RULE_05", inhibitions[0].description)
        print(f"Mirror Inhibition: {inhibitions[0].description}")

if __name__ == "__main__":
    unittest.main()
