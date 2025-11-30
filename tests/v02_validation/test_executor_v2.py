import unittest
import os
import shutil
from mace.runtime import executor
from mace.core import deterministic
from mace.memory import semantic

class TestExecutorV2(unittest.TestCase):
    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")
        deterministic.init_seed("exec_test_seed")
        
        # Cleanup
        if os.path.exists("logs/sem_write_journal.jsonl"):
            os.remove("logs/sem_write_journal.jsonl")
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")
        if os.path.exists("logs/reflective_log.jsonl"):
            os.remove("logs/reflective_log.jsonl")

    def tearDown(self):
        if os.path.exists("logs/sem_write_journal.jsonl"):
            os.remove("logs/sem_write_journal.jsonl")
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")
        if os.path.exists("logs/reflective_log.jsonl"):
            os.remove("logs/reflective_log.jsonl")

    def test_full_flow_math(self):
        """Verify full flow for math intent."""
        output, log = executor.execute("2 + 2")
        
        self.assertEqual(output["text"], "4")
        self.assertEqual(log["router_decision"]["selected_agents"][0]["agent_id"], "math_agent")
        self.assertEqual(log["router_decision"]["qcp_snapshot"]["intent_tags"], ["math_operation"])
        self.assertIn("log_id", log)

    def test_full_flow_profile_read(self):
        """Verify full flow for profile read with evidence."""
        # Setup SEM
        res = semantic.put_sem("user/profile/user_123/color", "green")
        self.assertTrue(res["success"], f"Setup put_sem failed: {res.get('error')}")
        
        output, log = executor.execute("what is my color")
        
        self.assertEqual(output["text"], "green")
        self.assertEqual(log["router_decision"]["selected_agents"][0]["agent_id"], "profile_agent")
        
        # Verify evidence
        self.assertEqual(len(log["evidence_items"]), 1)
        ev = log["evidence_items"][0]
        self.assertEqual(ev["type"], "sem_read_snapshot")
        self.assertEqual(ev["content"]["text"], '"green"')
        self.assertEqual(ev["source"]["reference"], "user/profile/user_123/color")

    def test_agent_failure_fallback(self):
        """Verify agent failure fallback."""
        # We can force failure by mocking the agent or passing input that causes crash
        # Math agent crashes on invalid syntax if we bypass regex?
        # Or we can mock the agent in the registry temporarily.
        
        original_agent = executor.AGENTS["math_agent"]
        
        class CrashingAgent:
            def run(self, percept):
                raise Exception("Simulated Crash")
                
        executor.AGENTS["math_agent"] = CrashingAgent()
        
        try:
            # "2 + 2" routes to math_agent, which will crash
            output, log = executor.execute("2 + 2")
            
            self.assertIn("partial answer", output["text"])
            self.assertEqual(len(log["errors"]), 1)
            self.assertIn("Simulated Crash", log["errors"][0]["message"])
            
        finally:
            executor.AGENTS["math_agent"] = original_agent

if __name__ == '__main__':
    unittest.main()
