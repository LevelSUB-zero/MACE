import unittest
from mace.router import stage1_router
from mace.core import deterministic

class TestRouter(unittest.TestCase):
    def setUp(self):
        deterministic.init_seed("router_test")
        
    def test_tie_breaking(self):
        # Two agents with identical capabilities/scores
        a1 = {"module_id": "agent_b", "capabilities": ["test"]}
        a2 = {"module_id": "agent_a", "capabilities": ["test"]}
        
        percept = {"percept_id": "p1", "text": "test command"}
        brainstate = {}
        
        # agent_a should win because 'agent_a' < 'agent_b' lexically
        decision = stage1_router.route(percept, brainstate, [a1, a2])
        
        self.assertEqual(len(decision["selected_agents"]), 1)
        self.assertEqual(decision["selected_agents"][0]["agent_id"], "agent_a")
        
    def test_scoring(self):
        # Profile agent should win for "update profile"
        a1 = {"module_id": "generic_agent", "capabilities": []}
        a2 = {"module_id": "profile_agent", "capabilities": ["profile"]}
        
        percept = {"percept_id": "p2", "text": "update profile"}
        decision = stage1_router.route(percept, {}, [a1, a2])
        
        self.assertEqual(decision["selected_agents"][0]["agent_id"], "profile_agent")

if __name__ == "__main__":
    unittest.main()
