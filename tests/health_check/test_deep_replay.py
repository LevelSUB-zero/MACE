import unittest
import json
import copy
from mace.core import deterministic, replay
from mace.runtime import executor

class TestDeepReplay(unittest.TestCase):
    
    def setUp(self):
        deterministic.init_seed("deep_replay_test")
        
    def test_deep_diff(self):
        # 1. Generate valid log
        # "what is 2+2" -> Math Agent
        res, log_entry = executor.execute("what is 2+2", seed="deep_seed")
        
        # 2. Mutate Agent Output (Reasoning Trace)
        mutated_log = copy.deepcopy(log_entry)
        # Assuming Math Agent produces output. It should.
        if mutated_log["agent_outputs"]:
            mutated_log["agent_outputs"][0]["reasoning_trace"] += " (mutated)"
            
            res = replay.replay_log(mutated_log)
            self.assertFalse(res["success"], "Should fail on mutated reasoning trace")
            self.assertEqual(res["error"], "AGENT_OUTPUT_MISMATCH")
            self.assertIn("mutated", res["details"])
        else:
            self.fail("No agent outputs generated")
        
        # 3. Mutate Router Decision
        mutated_log = copy.deepcopy(log_entry)
        mutated_log["router_decision"]["explain"] += " (mutated)"
        
        res = replay.replay_log(mutated_log)
        self.assertFalse(res["success"], "Should fail on mutated router explanation")
        self.assertEqual(res["error"], "ROUTING_MISMATCH")
        self.assertIn("mutated", res["details"])
        
        # 4. Mutate Final Output
        mutated_log = copy.deepcopy(log_entry)
        mutated_log["final_output"]["text"] += " (mutated)"
        
        res = replay.replay_log(mutated_log)
        self.assertFalse(res["success"], "Should fail on mutated final output")
        self.assertEqual(res["error"], "OUTPUT_MISMATCH")
        self.assertIn("mutated", res["details"])

if __name__ == "__main__":
    unittest.main()
