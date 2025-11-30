import unittest
import os
import shutil
from mace.agents import math_agent, profile_agent
from mace.core import structures, deterministic
from mace.memory import semantic

class TestAgentsV2(unittest.TestCase):
    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")
        deterministic.init_seed("agent_test_seed")
        
        # Cleanup SEM
        if os.path.exists("logs/sem_write_journal.jsonl"):
            os.remove("logs/sem_write_journal.jsonl")
        if os.path.exists("mace.db"):
            os.remove("mace.db")

    def tearDown(self):
        if os.path.exists("logs/sem_write_journal.jsonl"):
            os.remove("logs/sem_write_journal.jsonl")
        if os.path.exists("mace.db"):
            os.remove("mace.db")

    def test_math_agent(self):
        """Verify math agent output."""
        percept = {"text": "2 + 2"}
        output = math_agent.run(percept)
        
        self.assertEqual(output["agent_id"], "math_agent")
        self.assertEqual(output["text"], "4")
        self.assertIn("reasoning_trace", output)
        self.assertTrue(isinstance(output["reasoning_trace"], str))

    def test_profile_agent_write(self):
        """Verify profile agent write."""
        percept = {"text": "remember my color is blue"}
        output = profile_agent.run(percept)
        
        self.assertEqual(output["agent_id"], "profile_agent")
        self.assertIn("Stored color = blue", output["text"])
        self.assertIn("reasoning_trace", output)
        
        # Verify SEM write
        res = semantic.get_sem("user/profile/user_123/color")
        self.assertTrue(res["exists"])
        self.assertEqual(res["value"], "blue")

    def test_profile_agent_read(self):
        """Verify profile agent read."""
        # Setup
        semantic.put_sem("user/profile/user_123/color", "red")
        
        percept = {"text": "what is my color"}
        output = profile_agent.run(percept)
        
        self.assertEqual(output["agent_id"], "profile_agent")
        self.assertEqual(output["text"], "red")
        self.assertIn("reasoning_trace", output)

    def test_council_vote_stub(self):
        """Verify council vote generation."""
        vote = structures.create_council_vote("test_agent")
        
        self.assertEqual(vote["agent_id"], "test_agent")
        self.assertTrue(vote["approve"])
        self.assertEqual(vote["explain"], "stage0_stub")
        self.assertIn("vote_id", vote)

if __name__ == '__main__':
    unittest.main()
