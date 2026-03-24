import unittest
import copy
from mace.runtime import executor
from mace.core import replay
from mace.core import deterministic
from mace.memory import semantic

class TestReplayV2(unittest.TestCase):
    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")
        deterministic.init_seed("replay_test_seed")

    def test_replay_success(self):
        """Verify successful replay."""
        # 1. Generate a log
        output, log = executor.execute("2 + 2")
        
        # 2. Replay it
        result = replay.replay_log(log)
        self.assertTrue(result["success"], f"Replay failed: {result.get('error')}")

    def test_replay_with_evidence(self):
        """Verify replay with SEM evidence (no DB needed)."""
        # 1. Store a fact, then query it to generate a log with evidence
        semantic.put_sem("user/profile/user_123/color", "blue")
        output, log = executor.execute("what is my color")
        
        # Agent now returns full sentences like "Your color is blue."
        self.assertIn("blue", output["text"].lower())
            
        # Test 1: Exact replay should succeed
        result = replay.replay_log(log)
        self.assertTrue(result["success"], f"Replay failed: {result}")
        
        # Test 2: Corrupt evidence to prove replay uses it
        log_corrupt = copy.deepcopy(log)
        mod_count = 0
        for ev in log_corrupt["evidence_items"]:
            if "blue" in str(ev["content"].get("text", "")):
                ev["content"]["text"] = '"red"'
                ev["content"]["structured"] = "red"
                mod_count += 1
        
        if mod_count > 0:
            result = replay.replay_log(log_corrupt)
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "OUTPUT_MISMATCH")

    def test_replay_code_change_mismatch(self):
        """Verify replay fails if code logic changes."""
        output, log = executor.execute("2 + 2") # "4"
        
        # Mock agent to return "5"
        original_agent = executor.AGENTS["math_agent"]
        
        class BadMathAgent:
            def run(self, percept):
                from mace.core import structures
                return structures.create_agent_output("math_agent", "5", 1.0, "")
                
        executor.AGENTS["math_agent"] = BadMathAgent()
        
        try:
            result = replay.replay_log(log)
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "OUTPUT_MISMATCH")
            self.assertIn('"text": "5"', result["details"])
        finally:
            executor.AGENTS["math_agent"] = original_agent

if __name__ == '__main__':
    unittest.main()
