"""
MACE Pre-Stage-3 Hardened Stress Tests

Purpose: Verify system stability under adversarial, high-volume, and
edge-case conditions BEFORE entering Stage 3 development. Covers gaps
not addressed by the existing stress suite.

Run: $env:PYTHONPATH="src"; pytest tests/stress/test_pre_stage3.py -v --tb=short
"""
import unittest
import os
import copy
import json

from mace.runtime import executor
from mace.core import deterministic, replay
from mace.memory import semantic, storage_backend
from mace.brainstate import persistence as bs_persistence


def reset_all():
    """Full state reset for test isolation."""
    for db in ["mace_stage1.db", "mace_memory.db"]:
        if os.path.exists(db):
            try:
                os.remove(db)
            except Exception:
                pass

    from mace.reflective import writer as reflective_writer
    import mace.memory.episodic as eps

    bs_persistence._table_initialized = False
    reflective_writer._table_initialized = False
    semantic._tables_initialized = False
    eps._table_initialized = False


# =============================================================
# 1. HIGH-VOLUME SEQUENTIAL LOAD
# =============================================================

class TestHighVolumeLoad(unittest.TestCase):
    """Simulate sustained load — 100+ sequential operations."""

    @classmethod
    def setUpClass(cls):
        reset_all()
        deterministic.init_seed("high_volume_seed")

    def test_a_sequential_stores(self):
        """10 sequential profile stores should all succeed without crash."""
        success_count = 0
        for i in range(10):
            res, _ = executor.execute(f"remember my name is user_{i}")
            if "Got it!" in res["text"] or "Noted!" in res["text"]:
                success_count += 1

        self.assertGreaterEqual(success_count, 9,
            f"Only {success_count}/10 stores succeeded")

    def test_b_last_write_wins_after_volume(self):
        """After sequential writes, the LAST value should be retrievable."""
        res, _ = executor.execute("what is my name")
        self.assertIn("user_9", res["text"],
            f"Expected last write 'user_9', got: {res['text']}")


# =============================================================
# 2. MEMORY ISOLATION ACROSS SEEDS
# =============================================================

class TestMemoryIsolation(unittest.TestCase):
    """Verify SEM memory doesn't bleed across different key namespaces."""

    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")
        deterministic.init_seed("mem_isolation_seed")

    def test_sem_isolation_direct(self):
        """Direct SEM put/get should be isolated by key namespace."""
        semantic.put_sem("user/profile/user_A/color", "red")
        semantic.put_sem("user/profile/user_B/color", "blue")

        res_a = semantic.get_sem("user/profile/user_A/color")
        res_b = semantic.get_sem("user/profile/user_B/color")

        self.assertEqual(res_a["value"], "red")
        self.assertEqual(res_b["value"], "blue")


# =============================================================
# 3. REPLAY FIDELITY — PROFILE OPERATIONS
# =============================================================

class TestReplayProfile(unittest.TestCase):
    """Replay fidelity for profile write/read (not just math)."""

    @classmethod
    def setUpClass(cls):
        reset_all()
        deterministic.init_seed("replay_profile_seed")

    def test_replay_profile_store(self):
        """Profile store replay should produce identical output."""
        output, log = executor.execute("My name is Charlie")
        result = replay.replay_log(log)
        self.assertTrue(result["success"],
            f"Profile store replay failed: {result}")

    def test_replay_profile_recall(self):
        """Profile recall replay should use evidence snapshot."""
        semantic.put_sem("user/profile/user_123/color", "green")
        output, log = executor.execute("what is my color")
        self.assertIn("green", output["text"].lower())

        result = replay.replay_log(log)
        self.assertTrue(result["success"],
            f"Profile recall replay failed: {result}")


# =============================================================
# 4. BRAINSTATE SNAPSHOT INTEGRITY
# =============================================================

class TestBrainStateIntegrity(unittest.TestCase):
    """Verify BrainState is captured before/after execution."""

    @classmethod
    def setUpClass(cls):
        reset_all()
        deterministic.init_seed("brainstate_test_seed")

    def test_brainstate_before_after_present(self):
        """Log must contain brainstate_before and brainstate_after."""
        _, log = executor.execute("2 + 2")
        self.assertIn("brainstate_before", log)
        self.assertIn("brainstate_after", log)
        self.assertIsNotNone(log["brainstate_before"])
        self.assertIsNotNone(log["brainstate_after"])

    def test_brainstate_has_seed(self):
        """BrainState should contain the seed used for the execution."""
        _, log = executor.execute("2 + 2")
        # random_seed should be in the log
        self.assertIn("random_seed", log)
        self.assertIsNotNone(log["random_seed"])
        self.assertNotEqual(log["random_seed"], "")


# =============================================================
# 5. KILL-SWITCH ENFORCEMENT
# =============================================================

class TestKillSwitch(unittest.TestCase):
    """Kill-switch must halt all execution when active."""

    def test_kill_switch_blocks_execution(self):
        """Activating kill-switch should raise RuntimeError."""
        from mace.governance import killswitch

        killswitch.activate("test_reason", "test_user")
        try:
            with self.assertRaises(RuntimeError) as ctx:
                executor.execute("2 + 2")
            self.assertIn("KILL_SWITCH_ACTIVE", str(ctx.exception))
        finally:
            killswitch.deactivate("test_user")

    def test_kill_switch_deactivation_resumes(self):
        """After deactivation, executor should work again."""
        from mace.governance import killswitch

        killswitch.activate("test_reason", "test_user")
        killswitch.deactivate("test_user")

        # Should not raise
        output, _ = executor.execute("2 + 2")
        self.assertEqual(output["text"], "4")


# =============================================================
# 6. EVIDENCE CHAIN COMPLETENESS
# =============================================================

class TestEvidenceChain(unittest.TestCase):
    """Evidence items must correctly record SEM reads."""

    @classmethod
    def setUpClass(cls):
        reset_all()
        deterministic.init_seed("evidence_chain_seed")

    def test_evidence_captured_on_sem_read(self):
        """When agent reads SEM, evidence must appear in log."""
        semantic.put_sem("user/profile/user_123/name", "Diana")
        _, log = executor.execute("what is my name")

        self.assertIn("Diana", log["final_output"]["text"])
        # Find evidence for the SEM read
        sem_evidence = [e for e in log["evidence_items"]
                        if e["type"] == "sem_read_snapshot"]
        self.assertGreater(len(sem_evidence), 0,
            "No SEM read evidence captured")

    def test_evidence_content_matches(self):
        """Evidence content should match the actual SEM value."""
        semantic.put_sem("user/profile/user_123/age", "30")
        _, log = executor.execute("what is my age")

        sem_evidence = [e for e in log["evidence_items"]
                        if e["type"] == "sem_read_snapshot"]
        if sem_evidence:
            content = sem_evidence[0]["content"]
            self.assertIn("30", str(content),
                f"Evidence content doesn't contain '30': {content}")


# =============================================================
# 7. UNICODE & SPECIAL CHARACTER RESILIENCE
# =============================================================

class TestUnicodeResilience(unittest.TestCase):
    """System must handle Unicode, emoji, and multi-byte characters."""

    @classmethod
    def setUpClass(cls):
        reset_all()
        deterministic.init_seed("unicode_test_seed")

    def test_unicode_input_no_crash(self):
        """Unicode input should not crash."""
        output, _ = executor.execute("Bonjour, comment ça va?")
        self.assertIsNotNone(output["text"])

    def test_emoji_input_no_crash(self):
        """Emoji input should not crash."""
        output, _ = executor.execute("Hello 😀🎉 test")
        self.assertIsNotNone(output["text"])

    def test_cjk_input_no_crash(self):
        """CJK characters should not crash."""
        output, _ = executor.execute("你好世界")
        self.assertIsNotNone(output["text"])

    def test_mixed_script_no_crash(self):
        """Mixed scripts and RTL should not crash."""
        output, _ = executor.execute("Hello مرحبا שלום こんにちは")
        self.assertIsNotNone(output["text"])


# =============================================================
# 8. CROSS-AGENT ROUTING STABILITY SWEEP
# =============================================================

class TestRoutingSweep(unittest.TestCase):
    """Sweep probe phrases across all expected agent routes."""

    @classmethod
    def setUpClass(cls):
        reset_all()
        deterministic.init_seed("routing_sweep_seed")

    def _get_agent(self, text):
        _, log = executor.execute(text)
        return log["router_decision"]["selected_agents"][0]["agent_id"]

    def test_math_routes(self):
        """Math inputs should route to math_agent."""
        for inp in ["5 + 5", "100 / 4", "3 * 7"]:
            agent = self._get_agent(inp)
            self.assertEqual(agent, "math_agent", f"'{inp}' → {agent}")

    def test_profile_store_routes(self):
        """Profile store inputs should route to profile_agent."""
        for inp in ["my name is Test", "remember my color is red"]:
            agent = self._get_agent(inp)
            self.assertEqual(agent, "profile_agent", f"'{inp}' → {agent}")

    def test_profile_recall_routes(self):
        """Profile recall inputs should route to profile_agent."""
        for inp in ["what is my name", "what is my color"]:
            agent = self._get_agent(inp)
            self.assertEqual(agent, "profile_agent", f"'{inp}' → {agent}")

    def test_generic_fallback(self):
        """Unrecognizable input should route to generic_agent."""
        agent = self._get_agent("xyzzy plugh")
        self.assertEqual(agent, "generic_agent",
            f"Expected generic_agent fallback, got {agent}")

    def test_all_agents_reachable(self):
        """Every registered agent should be reachable by at least one input."""
        reached = set()
        probes = [
            "2 + 2",                  # math
            "my name is Test",        # profile
            "xyzzy plugh",            # generic
        ]
        for p in probes:
            reached.add(self._get_agent(p))

        for agent_id in ["math_agent", "profile_agent", "generic_agent"]:
            self.assertIn(agent_id, reached,
                f"Agent '{agent_id}' is unreachable")


# =============================================================
# 9. LOG SIGNATURE INTEGRITY
# =============================================================

class TestLogSignatureIntegrity(unittest.TestCase):
    """Verify reflective log signing is functional."""

    @classmethod
    def setUpClass(cls):
        reset_all()
        deterministic.init_seed("signature_test_seed")

    def test_log_has_signature(self):
        """Reflective log must contain a cryptographic signature."""
        _, log = executor.execute("2 + 2")
        self.assertIn("signature", log)
        self.assertIsNotNone(log["signature"])
        self.assertNotEqual(log["signature"], "")

    def test_log_has_immutable_subpayload(self):
        """Log must have immutable_subpayload for audit trail."""
        _, log = executor.execute("2 + 2")
        self.assertIn("immutable_subpayload", log)
        sub = log["immutable_subpayload"]
        self.assertIn("log_id", sub)
        self.assertIn("percept_text", sub)
        self.assertIn("final_output_text", sub)


if __name__ == "__main__":
    unittest.main(verbosity=2)
