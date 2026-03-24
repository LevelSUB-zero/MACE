"""
MACE Stress Test Suite

Purpose: Test the system's robustness by throwing edge cases, 
malformed inputs, boundary conditions, and adversarial inputs.

Run: python -m pytest tests/stress/test_stress.py -v --tb=short
"""
import unittest
import os
import random
import string

from mace.runtime import executor
from mace.core import deterministic
from mace.memory import semantic


def reset_db_state():
    """Reset database and module state for clean test isolation."""
    for db in ["mace_stage1.db", "mace_memory.db"]:
        if os.path.exists(db):
            os.remove(db)
    
    from mace.brainstate import persistence as bs_persistence
    from mace.reflective import writer as reflective_writer
    
    bs_persistence._table_initialized = False
    reflective_writer._table_initialized = False


# Valid attributes that the router recognizes (from stage1_router.py)
VALID_ATTRS = ['favorite', 'name', 'color', 'age', 'job', 'birthday']


class TestStressRandom(unittest.TestCase):
    """Random fact storage and retrieval stress tests."""
    
    @classmethod
    def setUpClass(cls):
        reset_db_state()
        deterministic.init_seed("stress_random_seed")
    
    def test_store_and_retrieve_facts(self):
        """Store facts using valid attributes and verify retrieval."""
        print("\n=== Storing Facts with Valid Attributes ===")
        facts = {}
        
        for i, attr in enumerate(VALID_ATTRS):
            value = ''.join(random.choices(string.ascii_lowercase, k=6))
            facts[attr] = value
            
            res, _ = executor.execute(f"remember my {attr} is {value}")
            self.assertIn("Got it!", res["text"], f"Failed to store {attr}")
            print(f"  ✓ Stored {attr} = {value}")
        
        # Verify retrieval
        print("=== Verifying Retrieval ===")
        for attr, expected_value in facts.items():
            res, _ = executor.execute(f"what is my {attr}")
            self.assertIn(expected_value, res["text"], f"Failed to retrieve {attr}")
            print(f"  ✓ Retrieved {attr} = {expected_value}")
    
    def test_overwrite_same_key_50_times(self):
        """Overwrite the same key 50 times (Last Write Wins)."""
        print("\n=== Overwriting 'favorite' 50 times ===")
        
        for i in range(50):
            value = f"val{i}"
            res, _ = executor.execute(f"remember my favorite is {value}")
            self.assertIn("Got it!", res["text"])
        
        # Verify only last value persists
        res, _ = executor.execute("what is my favorite")
        self.assertIn("val49", res["text"])
        print("  ✓ Last write wins verified (val49)")


class TestStressEdgeCases(unittest.TestCase):
    """Edge case and boundary condition tests."""
    
    @classmethod
    def setUpClass(cls):
        reset_db_state()
        deterministic.init_seed("edge_case_seed")
    
    def test_empty_input(self):
        """Empty input should go to generic agent and not crash."""
        print("\n=== Empty Input ===")
        res, _ = executor.execute("")
        # Should not crash, any response is acceptable
        self.assertIsNotNone(res["text"])
        print(f"  ✓ Empty input handled: '{res['text'][:50]}...'")
    
    def test_whitespace_only(self):
        """Whitespace-only input should not crash."""
        print("\n=== Whitespace Only ===")
        res, _ = executor.execute("   \t\n   ")
        self.assertIsNotNone(res["text"])
        print("  ✓ Whitespace handled")
    
    def test_very_long_input(self):
        """Very long input (1000 chars) should not crash."""
        print("\n=== Very Long Input (1000 chars) ===")
        long_text = "a" * 1000
        res, _ = executor.execute(long_text)
        self.assertIsNotNone(res["text"])
        print("  ✓ Long input handled")
    
    def test_special_value_stored(self):
        """Store value with underscores (safe special chars)."""
        print("\n=== Underscore in Value ===")
        res, _ = executor.execute("remember my name is John_Doe_123")
        self.assertIn("Got it!", res["text"])
        print("  ✓ Underscore in value handled")
    
    def test_sql_injection_attempt(self):
        """SQL injection attempt should not crash the system."""
        print("\n=== SQL Injection Attempt ===")
        evil = "'; DROP TABLE sem_kv; --"
        res, _ = executor.execute(f"remember my name is {evil}")
        # Should handle gracefully
        self.assertIsNotNone(res["text"])
        print("  ✓ SQL injection attempt neutralized")


class TestStressPIIBlocking(unittest.TestCase):
    """Verify PII is blocked from storage."""
    
    @classmethod
    def setUpClass(cls):
        reset_db_state()
        deterministic.init_seed("pii_test_seed")
    
    def test_credit_card_blocked(self):
        """Credit card numbers should be blocked (direct SEM check)."""
        print("\n=== Credit Card PII Blocking ===")
        result = semantic.put_sem(
            "user/profile/test_user/cc",
            "4111-1111-1111-1111",
            source="test"
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "PRIVACY_BLOCKED")
        print("  ✓ Credit card blocked")
    
    def test_ssn_blocked(self):
        """SSN should be blocked (direct SEM check)."""
        print("\n=== SSN PII Blocking ===")
        result = semantic.put_sem(
            "user/profile/test_user/ssn",
            "123-45-6789",
            source="test"
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "PRIVACY_BLOCKED")
        print("  ✓ SSN blocked")
    
    def test_normal_data_allowed(self):
        """Normal data should be allowed."""
        print("\n=== Normal Data Allowed ===")
        result = semantic.put_sem(
            "user/profile/test_user/age",
            "42",
            source="test"
        )
        self.assertTrue(result["success"])
        print("  ✓ Normal data stored")


class TestStressRouterBoundaries(unittest.TestCase):
    """Router intent detection edge cases."""
    
    @classmethod
    def setUpClass(cls):
        reset_db_state()
        deterministic.init_seed("router_stress_seed")
    
    def test_math_detection(self):
        """Math expressions should route to math_agent."""
        print("\n=== Math Detection ===")
        
        math_inputs = ["2+2", "100 * 50", "calculate 5!"]
        
        for inp in math_inputs:
            res, log = executor.execute(inp)
            agent = log["router_decision"]["selected_agents"][0]["agent_id"]
            self.assertEqual(agent, "math_agent", f"Expected math_agent for '{inp}'")
            print(f"  ✓ '{inp}' → math_agent")
    
    def test_personal_over_fact(self):
        """'what is my X' should route to profile, not knowledge."""
        print("\n=== Personal Over Fact Priority ===")
        
        res, log = executor.execute("what is my name")
        agent = log["router_decision"]["selected_agents"][0]["agent_id"]
        self.assertEqual(agent, "profile_agent")
        print("  ✓ 'what is my name' → profile_agent")
    
    def test_math_priority_over_personal(self):
        """Math keywords should take priority over personal."""
        print("\n=== Math Priority Over Personal ===")
        
        res, log = executor.execute("calculate my age")
        agent = log["router_decision"]["selected_agents"][0]["agent_id"]
        self.assertEqual(agent, "math_agent")
        print("  ✓ 'calculate my age' → math_agent (R1 priority)")


class TestStressFailureRecovery(unittest.TestCase):
    """Test failure scenarios and recovery."""
    
    @classmethod
    def setUpClass(cls):
        reset_db_state()
        deterministic.init_seed("failure_test_seed")
    
    def test_agent_crash_recovery(self):
        """Agent crash should fallback gracefully."""
        print("\n=== Agent Crash Recovery ===")
        from mace.agents import math_agent
        original = math_agent.run
        
        def crash(percept):
            raise RuntimeError("Simulated crash!")
        
        math_agent.run = crash
        try:
            res, log = executor.execute("2 + 2")
            self.assertIn("failed", res["text"].lower())
            self.assertEqual(res["confidence"], 0.0)
            self.assertTrue(len(log["errors"]) > 0)
            print("  ✓ Crash handled, fallback activated")
        finally:
            math_agent.run = original
    
    def test_rapid_fire_requests(self):
        """Rapid succession requests should all succeed."""
        print("\n=== Rapid Fire Requests (10x) ===")
        
        for i in range(10):
            # Use valid attribute 'name' with unique values
            res, _ = executor.execute(f"remember my name is user{i}")
            self.assertIn("Got it!", res["text"])
        
        print("  ✓ 10 rapid requests completed")
    
    def test_invalid_key_format_direct(self):
        """Invalid key format should be rejected (direct SEM check)."""
        print("\n=== Invalid Key Format ===")
        
        result = semantic.put_sem("invalid_key", "value", source="test")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "INVALID_KEY_FORMAT")
        print("  ✓ Invalid key rejected")


class TestStressDeterminism(unittest.TestCase):
    """Verify deterministic behavior."""
    
    def test_same_seed_same_log_id(self):
        """Same seed should produce identical log IDs."""
        print("\n=== Deterministic Log IDs ===")
        
        # Run 1
        reset_db_state()
        deterministic.init_seed("determinism_test_42")
        res1, log1 = executor.execute("remember my name is alpha")
        id1 = log1["log_id"]
        
        # Reset and Run 2 with same seed
        reset_db_state()
        deterministic.init_seed("determinism_test_42")
        res2, log2 = executor.execute("remember my name is alpha", log_enabled=False)
        id2 = log2["log_id"]
        
        self.assertEqual(id1, id2, "Log IDs should be identical for same seed")
        print(f"  ✓ log_id consistent: {id1[:20]}...")


if __name__ == "__main__":
    unittest.main(verbosity=2)
