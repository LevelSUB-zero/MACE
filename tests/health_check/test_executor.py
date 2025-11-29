import unittest
import json
from mace.core import deterministic, structures
from mace.runtime import executor
from mace.agents import math_agent

class TestExecutor(unittest.TestCase):
    
    def setUp(self):
        deterministic.init_seed("executor_test_seed")

    def test_5_1_agent_crash_handling(self):
        """
        5.1 — Agent crash handling
        Force agent to raise. Assert errors[] contains ExtendedErrorEvent.
        Fallback to generic_agent occurs.
        """
        # Monkeypatch math_agent
        original_run = math_agent.run
        
        def fail_run(percept):
            raise RuntimeError("Forced Crash")
            
        math_agent.run = fail_run
        
        try:
            res, log_entry = executor.execute("2+2", log_enabled=False)
            
            # Check error log
            self.assertTrue(len(log_entry["errors"]) > 0)
            error = log_entry["errors"][0]
            self.assertEqual(error["message"], "Agent math_agent failed: Forced Crash")
            self.assertEqual(error["severity"], "error")
            
            # Check fallback
            self.assertIn("One of my internal modules failed", res["text"])
            self.assertEqual(res["confidence"], 0.0)
            
            print("\nPASS: Agent crash handling")
            
        finally:
            math_agent.run = original_run

    def test_5_2_council_stub_correctness(self):
        """
        5.2 — Council stub correctness
        Ensure council emits one deterministic vote with approve=true.
        """
        res, log_entry = executor.execute("2+2", log_enabled=False)
        
        votes = log_entry["council_votes"]
        self.assertEqual(len(votes), 1)
        vote = votes[0]
        self.assertTrue(vote["approve"])
        self.assertEqual(vote["correctness"], 1.0)
        self.assertEqual(vote["safety"], 1.0)
        
        print("PASS: Council stub correctness")

    def test_5_3_final_selection_tie_break(self):
        """
        5.3 — Final selection deterministic tie‑break
        Simulate two agent outputs with same confidence.
        """
        # Create dummy outputs
        out1 = structures.create_agent_output("agent_b", "Output B", confidence=0.9)
        out2 = structures.create_agent_output("agent_a", "Output A", confidence=0.9)
        
        # Tie-break: lowest lexicographical agent_id wins -> agent_a
        final = executor.select_final_output([out1, out2])
        self.assertEqual(final["text"], "Output A")
        
        # Tie-break: highest confidence wins
        out3 = structures.create_agent_output("agent_c", "Output C", confidence=0.95)
        final = executor.select_final_output([out1, out2, out3])
        self.assertEqual(final["text"], "Output C")
        
        print("PASS: Final selection tie-break")

if __name__ == "__main__":
    unittest.main()
