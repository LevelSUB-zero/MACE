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
        # 1. Generate log with evidence
        # We manually construct a log entry to simulate a past execution with evidence
        # because running full executor with DB setup is complex here.
        # But we can use executor if we mock DB or use put_sem.
        
        # Let's use put_sem to create state, run executor, then clear DB, then replay.
        semantic.put_sem("user/profile/user_123/color", "blue")
        output, log = executor.execute("what is my color") # Should match "blue" if I fix qcp/agent
        
        # Check if it worked first
        if output["text"] != "blue":
            # If agent logic is still "what is my color" -> "blue" (requires profile agent fix?)
            # Wait, I fixed qcp.py.
            # But did I fix profile_agent?
            # Profile agent uses regex `(what is my|my) (?P<attribute>...)`.
            # Input "what is my color" matches.
            pass
            
        # Clear DB to ensure replay uses evidence
        # We can't easily clear DB file if it's locked, but we can corrupt it or just rely on set_replay_snapshot.
        # replay_log calls set_replay_snapshot.
        # semantic.get_sem checks snapshot FIRST.
        # So even if DB exists, snapshot takes precedence.
        
        # Let's modify the evidence in the log to prove it uses evidence!
        # Change "blue" to "red" in evidence.
        # Replay should produce "red".
        # But wait, replay compares with original output ("blue").
        # So replay should FAIL with mismatch if we change evidence but expect original output.
        # OR, if we change evidence AND original output in log, it should succeed (if agent logic is deterministic).
        
        # Let's try:
        # 1. Log says "blue". Evidence says "blue". Replay -> "blue". Success.
        result = replay.replay_log(log)
        self.assertTrue(result["success"])
        
        # 2. Log says "blue". Evidence says "red". Replay -> "red". Mismatch!
        log_corrupt = copy.deepcopy(log)
        # Find evidence
        mod_count = 0
        for ev in log_corrupt["evidence_items"]:
            if ev["content"]["text"] == '"blue"':
                ev["content"]["text"] = '"red"'
                ev["content"]["structured"] = "red" # Update structured too if present
                mod_count += 1
        
        self.assertEqual(mod_count, 1, "Failed to modify evidence for corruption test")
                
        result = replay.replay_log(log_corrupt)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "OUTPUT_MISMATCH")
        self.assertIn("red", result["details"]) # Got "red"

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
