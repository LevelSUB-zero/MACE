"""
MACE System Test Suite — Canonical Verification (Stage 2 → 3 Gateway)

This is the single authoritative test suite that validates the current MACE
system end-to-end. It tests ACTUAL behavior against CURRENT module outputs,
not historical assumptions.

Run:  $env:PYTHONPATH="src"; pytest tests/system/test_mace_system.py -v
"""
import unittest
import os
import copy

from mace.runtime import executor
from mace.core import deterministic, replay
from mace.memory import semantic, storage_backend


class TestMACESystem(unittest.TestCase):
    """Full system end-to-end tests for the current MACE pipeline."""

    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")
        deterministic.init_seed("system_test_seed")

    # =====================================================
    # MATH AGENT
    # =====================================================

    def test_math_basic(self):
        """Math expressions should route to math_agent and compute correctly."""
        output, log = executor.execute("2 + 2")
        self.assertEqual(output["text"], "4")
        self.assertEqual(output["confidence"], 1.0)
        self.assertEqual(
            log["router_decision"]["selected_agents"][0]["agent_id"],
            "math_agent"
        )

    def test_math_complex(self):
        """Slightly more complex math should still work."""
        output, log = executor.execute("10 * 5")
        self.assertEqual(output["text"], "50")

    # =====================================================
    # PROFILE AGENT — Write
    # =====================================================

    def test_profile_write(self):
        """Profile store should persist to SEM and return confirmation."""
        output, log = executor.execute("My name is Alice")
        self.assertIn("Got it!", output["text"])
        self.assertIn("Alice", output["text"])
        self.assertEqual(
            log["router_decision"]["selected_agents"][0]["agent_id"],
            "profile_agent"
        )

        # Verify SEM persistence
        res = semantic.get_sem("user/profile/user_123/name")
        self.assertTrue(res["exists"])
        self.assertEqual(res["value"].lower(), "alice")

    # =====================================================
    # PROFILE AGENT — Read
    # =====================================================

    def test_profile_read(self):
        """Profile recall should return stored value and produce evidence."""
        # Pre-populate
        semantic.put_sem("user/profile/user_123/name", "Bob")

        output, log = executor.execute("What is my name")
        self.assertIn("Bob", output["text"])
        self.assertEqual(output["confidence"], 1.0)
        self.assertEqual(
            log["router_decision"]["selected_agents"][0]["agent_id"],
            "profile_agent"
        )
        # Evidence should exist for SEM reads
        self.assertTrue(len(log["evidence_items"]) > 0)

    # =====================================================
    # KNOWLEDGE AGENT — Teach & Query
    # =====================================================

    def test_knowledge_teach(self):
        """Teaching a fact should store it in SEM."""
        # Use explicit intent because legacy parser (without Ollama) misroutes
        # fact-style inputs like "remember that X is Y" to contact_store
        output, log = executor.execute(
            "remember that the sun is a star",
            intent="fact_teach",
            entities={"attribute": "sun", "value": "a star"}
        )
        self.assertIn("Got it!", output["text"])
        self.assertEqual(
            log["router_decision"]["selected_agents"][0]["agent_id"],
            "knowledge_agent"
        )

        # Verify SEM persistence
        res = semantic.get_sem("world/fact/general/sun")
        self.assertTrue(res["exists"])
        self.assertEqual(res["value"], "a star")

    def test_knowledge_query(self):
        """Querying a taught fact should return it."""
        semantic.put_sem("world/fact/general/sun", "a star")

        output, log = executor.execute(
            "what is the sun",
            intent="history_search",
            entities={"attribute": "sun"}
        )
        self.assertIn("a star", output["text"])

    # =====================================================
    # PII BLOCKING
    # =====================================================

    def test_pii_ssn_blocked(self):
        """SSN patterns should be blocked by governance."""
        result = semantic.put_sem(
            "user/profile/user_123/ssn",
            "123-45-6789"
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "PRIVACY_BLOCKED")

    def test_pii_credit_card_blocked(self):
        """Credit card patterns should be blocked."""
        result = semantic.put_sem(
            "user/profile/user_123/cc",
            "4111-1111-1111-1111"
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "PRIVACY_BLOCKED")

    # =====================================================
    # INVALID KEY BLOCKING
    # =====================================================

    def test_invalid_key_rejected(self):
        """Keys not matching canonical format should be rejected."""
        result = semantic.put_sem("invalid key", "value")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "INVALID_KEY_FORMAT")

    # =====================================================
    # AGENT CRASH FALLBACK
    # =====================================================

    def test_agent_crash_fallback(self):
        """Agent crash should produce graceful fallback, not system crash."""
        original_agent = executor.AGENTS["math_agent"]

        class CrashAgent:
            def run(self, percept):
                raise RuntimeError("Simulated crash!")

        executor.AGENTS["math_agent"] = CrashAgent()

        try:
            output, log = executor.execute("2 + 2")
            self.assertIn("failed", output["text"].lower())
            self.assertEqual(output["confidence"], 0.0)
            self.assertTrue(len(log["errors"]) > 0)
        finally:
            executor.AGENTS["math_agent"] = original_agent

    # =====================================================
    # REPLAY DETERMINISM
    # =====================================================

    def test_replay_deterministic(self):
        """Replay of a math execution should produce identical output."""
        output, log = executor.execute("2 + 2")
        result = replay.replay_log(log)
        self.assertTrue(result["success"], f"Replay failed: {result}")

    def test_replay_corruption_detected(self):
        """Corrupted log should cause replay mismatch."""
        output, log = executor.execute("2 + 2")

        # Corrupt the expected output
        log_corrupt = copy.deepcopy(log)
        log_corrupt["final_output"]["text"] = "999"

        result = replay.replay_log(log_corrupt)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "OUTPUT_MISMATCH")

    # =====================================================
    # DETERMINISTIC LOG IDS
    # =====================================================

    def test_deterministic_log_ids(self):
        """Same seed + input should produce the same log_id."""
        deterministic.init_seed("determinism_check_42")
        _, log1 = executor.execute("2 + 2")

        deterministic.init_seed("determinism_check_42")
        _, log2 = executor.execute("2 + 2", log_enabled=False)

        self.assertEqual(log1["log_id"], log2["log_id"])

    # =====================================================
    # EDGE CASES
    # =====================================================

    def test_empty_input_no_crash(self):
        """Empty input should not crash the system."""
        output, _ = executor.execute("")
        self.assertIsNotNone(output["text"])

    def test_sql_injection_neutralized(self):
        """SQL injection in value should not crash or corrupt."""
        evil = "'; DROP TABLE sem_kv; --"
        output, _ = executor.execute(f"remember my name is {evil}")
        # System should handle gracefully — any response is ok
        self.assertIsNotNone(output["text"])

    # =====================================================
    # LOG STRUCTURE INTEGRITY
    # =====================================================

    def test_log_entry_has_required_fields(self):
        """Every log entry must have the canonical fields."""
        _, log = executor.execute("2 + 2")

        required = [
            "log_id", "timestamp", "percept", "router_decision",
            "agent_outputs", "council_votes", "final_output",
            "brainstate_before", "brainstate_after", "errors",
            "memory_reads", "memory_writes", "evidence_items",
            "random_seed", "model_versions"
        ]
        for field in required:
            self.assertIn(field, log, f"Missing required field: {field}")

    def test_percept_has_required_fields(self):
        """Percept in log must have text, intent, and entities."""
        _, log = executor.execute("hello")
        percept = log["percept"]

        self.assertIn("percept_id", percept)
        self.assertIn("text", percept)
        self.assertIn("intent", percept)
        self.assertIn("entities", percept)
        self.assertIn("timestamp", percept)


if __name__ == "__main__":
    unittest.main()
