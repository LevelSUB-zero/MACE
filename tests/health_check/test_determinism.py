import unittest
import json
from mace.core import deterministic
from mace.runtime import executor

class TestDeterminism(unittest.TestCase):
    
    def test_1_1_seed_repeatability(self):
        """
        1.1 — Seed repeatability
        Run a deterministic request twice with the same seed.
        Compare generated log_id, router_decision.decision_id, agent_output.agent_id, final_output.text, random_seed.
        """
        seed = "seed-A"
        query = "What's my favorite color?"
        
        # Run 1
        deterministic.init_seed(seed)
        res1, log1 = executor.execute(query, seed=seed, log_enabled=False)
        
        # Run 2
        deterministic.init_seed(seed)
        res2, log2 = executor.execute(query, seed=seed, log_enabled=False)
        
        # Compare
        self.assertEqual(log1["log_id"], log2["log_id"], "log_id mismatch")
        self.assertEqual(log1["router_decision"]["decision_id"], log2["router_decision"]["decision_id"], "decision_id mismatch")
        
        # Agent output ID is not directly in final_output, but in log -> agent_outputs
        # Assuming single agent selection
        agent_out1 = log1["router_decision"]["selected_agents"][0]["agent_id"]
        agent_out2 = log2["router_decision"]["selected_agents"][0]["agent_id"]
        self.assertEqual(agent_out1, agent_out2, "agent_id mismatch")
        
        self.assertEqual(res1["text"], res2["text"], "final_output text mismatch")
        self.assertEqual(log1["random_seed"], log2["random_seed"], "random_seed mismatch")
        
        print("\nPASS: seed repeatability — log_id identical: " + log1["log_id"])

    def test_1_3_deterministic_timestamp(self):
        """
        1.3 — Deterministic timestamp check
        Using same seed and counter, compute deterministic_timestamp(seed, counter) twice.
        """
        seed = "seed-B"
        counter = 42
        
        deterministic.init_seed(seed)
        ts1 = deterministic.deterministic_timestamp(counter)
        
        deterministic.init_seed(seed)
        ts2 = deterministic.deterministic_timestamp(counter)
        
        self.assertEqual(ts1, ts2, "Timestamps must be identical for same seed/counter")
        
        # Check ISO format (basic check)
        # 2025-01-01T...
        self.assertIn("T", ts1)
        self.assertIn("+00:00", ts1) # UTC
        
        print(f"\nPASS: deterministic timestamp: {ts1}")

if __name__ == "__main__":
    unittest.main()
