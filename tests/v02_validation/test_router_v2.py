import unittest
from mace.core import router, deterministic

class TestRouterV2(unittest.TestCase):
    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")
        deterministic.init_seed("router_test_seed")

    def test_route_math(self):
        """Verify routing for math intent."""
        percept = {"percept_id": "p1"}
        qcp_snapshot = {"features": {"math": True}}
        
        decision = router.route_percept(percept, qcp_snapshot)
        
        self.assertEqual(decision["selected_agents"][0]["agent_id"], "math_agent")
        self.assertEqual(decision["explain"], "matched_R1_math")
        self.assertIn("decision_id", decision)

    def test_route_profile(self):
        """Verify routing for profile intent."""
        percept = {"percept_id": "p2"}
        qcp_snapshot = {"features": {"profile": True}}
        
        decision = router.route_percept(percept, qcp_snapshot)
        
        self.assertEqual(decision["selected_agents"][0]["agent_id"], "profile_agent")
        self.assertEqual(decision["explain"], "matched_R2_profile")

    def test_route_fact(self):
        """Verify routing for fact intent."""
        percept = {"percept_id": "p3"}
        qcp_snapshot = {"features": {"fact": True}}
        
        decision = router.route_percept(percept, qcp_snapshot)
        
        self.assertEqual(decision["selected_agents"][0]["agent_id"], "knowledge_agent")
        self.assertEqual(decision["explain"], "matched_R3_knowledge")

    def test_route_fallback(self):
        """Verify fallback routing."""
        percept = {"percept_id": "p4"}
        qcp_snapshot = {"features": {}}
        
        decision = router.route_percept(percept, qcp_snapshot)
        
        self.assertEqual(decision["selected_agents"][0]["agent_id"], "generic_agent")
        self.assertEqual(decision["explain"], "matched_R4_fallback")

    def test_decision_structure(self):
        """Verify ExtendedRouterDecision structure."""
        percept = {"percept_id": "p_struct"}
        qcp_snapshot = {"features": {"math": True}, "depth_level": 1}
        
        decision = router.route_percept(percept, qcp_snapshot)
        
        required_keys = [
            "decision_id", "percept_id", "selected_agents", "qcp_snapshot",
            "router_features_used", "depth_level", "memory_strategy",
            "budget", "explain", "created_at", "random_seed"
        ]
        for key in required_keys:
            self.assertIn(key, decision)
            
        self.assertEqual(decision["memory_strategy"], "sem_only")
        self.assertEqual(decision["qcp_snapshot"], qcp_snapshot)
        self.assertEqual(decision["router_features_used"], ["math"])

    def test_determinism(self):
        """Verify decision_id is deterministic."""
        deterministic.init_seed("det_seed")
        percept = {"percept_id": "p_det"}
        qcp_snapshot = {"features": {}}
        
        d1 = router.route_percept(percept, qcp_snapshot)
        
        deterministic.init_seed("det_seed")
        d2 = router.route_percept(percept, qcp_snapshot)
        
        self.assertEqual(d1["decision_id"], d2["decision_id"])
        self.assertEqual(d1["created_at"], d2["created_at"])

if __name__ == '__main__':
    unittest.main()
