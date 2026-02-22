
import sys
import unittest
sys.path.insert(0, r"f:\MAIN PROJECTS\Mace\src")

from mace.core.cognitive.cortex import ShadowCortex
from mace.core.cognitive.frame import CognitiveFrame, GoalNode

class TestHippocampalLearning(unittest.TestCase):
    def setUp(self):
        self.cortex = ShadowCortex(job_seed="learn_test")
        
    def test_memory_storage(self):
        """
        Verify that thoughts are stored in episodic memory.
        """
        self.cortex.process_active_thought({"text": "Hello"})
        
        memories = self.cortex.hippocampus.retrieve_recent()
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["outcome"], "active")
        print(f"Stored Memory: {memories[0]}")

    def test_sleep_consolidation(self):
        """
        Verify that Sleep Cycle generates insights from failure.
        """
        # Inject a fake failure memory
        fake_frame = self.cortex._create_frame()
        fake_frame.active_goal = GoalNode(
            goal_id="g1", statement="open_airlock", success_criteria=[], status="failed"
        )
        
        self.cortex.hippocampus.store(
            fake_frame, 
            op="FORCE_OPEN", 
            outcome="failed" # Simulation of a bad outcome
        )
        
        # Trigger Sleep
        insights = self.cortex.sleep()
        
        print(f"Sleep Insights: {insights}")
        
        # Verify Learning
        self.assertTrue(len(insights) > 0)
        self.assertIn("INHIBITED", insights[0])
        self.assertIn("FORCE_OPEN", insights[0])

if __name__ == "__main__":
    unittest.main()
