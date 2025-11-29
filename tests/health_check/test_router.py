import unittest
import json
from mace.core import deterministic, structures
from mace.router import router_stage0
from mace.runtime import executor

class TestRouter(unittest.TestCase):
    
    def setUp(self):
        deterministic.init_seed("router_test_seed")

    def test_4_1_rule_match_precision(self):
        """
        4.1 — Rule match precision
        Test cases for math, profile, knowledge, generic.
        """
        cases = [
            ("2+2", "math_agent", "matched_R1_math", "regex_match_R1"),
            ("Solve 10 ^ 2", "math_agent", "matched_R1_math", "regex_match_R1"), # Wait, "Solve " might break regex?
            # Regex: ^\s*\d+\s*([+\-*/^])\s*\d+\s*$
            # "Solve 10 ^ 2" does NOT match this regex.
            # So it should go to Generic.
            # Let's verify what the spec says vs code.
            # Spec R1: ^\s*\d+\s*([+\-*/^])\s*\d+\s*$
            # So "Solve ..." is NOT math.
            # I will expect Generic for "Solve 10 ^ 2".
            
            ("What's my favorite color?", "profile_agent", "matched_R2_profile", "regex_match_R2"),
            ("remember my favorite_color is blue", "profile_agent", "matched_R2_profile", "regex_match_R2"),
            ("What is Ohm's law?", "knowledge_agent", "matched_R3_knowledge", "regex_match_R3"),
            ("random question", "generic_agent", "matched_R4_fallback", "rule_match_fallback")
        ]
        
        for text, expected_agent, expected_why, expected_feature in cases:
            percept = structures.create_percept(text)
            brainstate = structures.create_brainstate()
            decision = router_stage0.route(percept, brainstate)
            
            # For "Solve 10 ^ 2", if code is strict, it's Generic.
            # If I want it to be Math, I'd need to change regex.
            # But I should test what IS implemented.
            # I'll handle the "Solve" case specifically.
            if text == "Solve 10 ^ 2":
                # Current regex is strict.
                self.assertEqual(decision["selected_agents"][0]["agent_id"], "generic_agent")
            else:
                self.assertEqual(decision["selected_agents"][0]["agent_id"], expected_agent, f"Failed for {text}")
                self.assertEqual(decision["explain"], expected_why)
                self.assertIn(expected_feature, decision["router_features_used"])
                
        print("\nPASS: Router rule match precision")

    def test_4_2_math_grammar(self):
        """
        4.2 — Math agent limited grammar
        Allowed: 3+4, 10/2, 5 ^ 2
        Disallowed: 2.5+3.1, (2+3)*4, 2+
        """
        allowed = ["3+4", "10/2", "5 ^ 2"]
        disallowed = ["2.5+3.1", "(2+3)*4", "2+"]
        
        for text in allowed:
            res, _ = executor.execute(text, log_enabled=False)
            # Should be math agent
            # And produce result
            # 3+4=7, 10/2=5.0, 5^2=25
            # Just check it didn't fallback to generic text "I don't have enough..."
            # Math agent returns result as text.
            self.assertNotIn("I don’t have enough stored info", res["text"])
            
        for text in disallowed:
            res, _ = executor.execute(text, log_enabled=False)
            # Should be generic agent because regex won't match
            self.assertIn("I don’t have enough stored info", res["text"])
            
        print("PASS: Math grammar")

    def test_4_3_profile_regex(self):
        """
        4.3 — Profile write detection deterministic regex
        Exact match: remember my favorite_color is blue
        Variant: remember me favourite colour = blue (Should fail)
        """
        # Exact
        res, _ = executor.execute("remember my favorite_color is blue", log_enabled=False)
        self.assertIn("Stored favorite_color = blue", res["text"])
        
        # Variant
        res, _ = executor.execute("remember me favourite colour = blue", log_enabled=False)
        # Should be generic
        self.assertIn("I don’t have enough stored info", res["text"])
        
        print("PASS: Profile regex")

    def test_4_4_budget_brainstate(self):
        """
        4.4 — Budget sanity & brainstate propagation
        """
        percept = structures.create_percept("2+2")
        brainstate = structures.create_brainstate()
        decision = router_stage0.route(percept, brainstate)
        
        self.assertGreaterEqual(decision["budget"]["token_budget"], 1)
        self.assertEqual(decision["brainstate_snapshot"], brainstate)
        
        print("PASS: Budget & Brainstate")

if __name__ == "__main__":
    unittest.main()
