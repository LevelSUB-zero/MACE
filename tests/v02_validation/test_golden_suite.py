import unittest
import os
import copy
from mace.runtime import executor
from mace.core import deterministic, replay
from mace.memory import semantic, storage_backend

class TestGoldenSuite(unittest.TestCase):
    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")
        deterministic.init_seed("golden_suite_seed")
        
        # Cleanup
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")
        if os.path.exists("logs/sem_write_journal.jsonl"):
            os.remove("logs/sem_write_journal.jsonl")
        if os.path.exists("logs/reflective_log.jsonl"):
            os.remove("logs/reflective_log.jsonl")

    def tearDown(self):
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")
        if os.path.exists("logs/sem_write_journal.jsonl"):
            os.remove("logs/sem_write_journal.jsonl")
        if os.path.exists("logs/reflective_log.jsonl"):
            os.remove("logs/reflective_log.jsonl")

    # --- Golden Tests ---

    def test_g1_math(self):
        """G1: Math Operation"""
        output, log = executor.execute("2 + 2")
        self.assertEqual(output["text"], "4")
        self.assertEqual(log["router_decision"]["selected_agents"][0]["agent_id"], "math_agent")

    def test_g2_profile_write(self):
        """G2: Profile Write"""
        output, log = executor.execute("My name is Alice")
        self.assertIn("Stored", output["text"])
        self.assertEqual(log["router_decision"]["selected_agents"][0]["agent_id"], "profile_agent")
        
        # Verify persistence
        res = semantic.get_sem("user/profile/user_123/name")
        self.assertTrue(res["exists"])
        self.assertEqual(res["value"], "alice")

    def test_g3_profile_read(self):
        """G3: Profile Read"""
        # Setup
        semantic.put_sem("user/profile/user_123/name", "alice")
        
        output, log = executor.execute("What is my name")
        self.assertEqual(output["text"], "alice")
        self.assertEqual(log["router_decision"]["selected_agents"][0]["agent_id"], "profile_agent")
        self.assertTrue(len(log["evidence_items"]) > 0)

    def test_g4_fact(self):
        """G4: Fact (Not Found)"""
        output, log = executor.execute("What is the capital of France")
        self.assertIn("I don’t have this information", output["text"])
        self.assertEqual(log["router_decision"]["selected_agents"][0]["agent_id"], "knowledge_agent")

    # --- Failure Tests ---

    def test_t16_pii_block(self):
        """T16: PII Blocking"""
        res = semantic.put_sem("user/profile/user_123/ssn", "123-45-6789")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "PRIVACY_BLOCKED")

    def test_t17_invalid_key(self):
        """T17: Invalid Key Format"""
        # Direct call
        res = semantic.put_sem("invalid key", "value")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "INVALID_KEY_FORMAT")

    def test_t18_agent_timeout(self):
        """T18: Agent Timeout (Simulated)"""
        original_agent = executor.AGENTS["math_agent"]
        
        class TimeoutAgent:
            def run(self, percept):
                raise Exception("TIMEOUT: Agent took too long")
                
        executor.AGENTS["math_agent"] = TimeoutAgent()
        
        try:
            output, log = executor.execute("2 + 2")
            self.assertIn("timed out", output["text"])
            self.assertEqual(log["errors"][0]["severity"], "warning")
        finally:
            executor.AGENTS["math_agent"] = original_agent

    def test_t19_db_write_fail(self):
        """T19: DB Write Failure (Simulated)"""
        # Mock StorageBackend.put to return False
        original_put = storage_backend.StorageBackend.put
        
        def mock_put(self, key, value, ts):
            return False
            
        storage_backend.StorageBackend.put = mock_put
        
        try:
            res = semantic.put_sem("user/profile/user_123/test", "value")
            self.assertFalse(res["success"])
            self.assertEqual(res["error"], "DB_WRITE_FAILED")
        finally:
            storage_backend.StorageBackend.put = original_put

    def test_t20_replay_mismatch(self):
        """T20: Replay Mismatch"""
        output, log = executor.execute("2 + 2")
        
        # Corrupt log evidence
        # Math agent doesn't use evidence, so we corrupt output text in log
        log_corrupt = copy.deepcopy(log)
        log_corrupt["final_output"]["text"] = "5"
        
        result = replay.replay_log(log_corrupt)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "OUTPUT_MISMATCH")

if __name__ == '__main__':
    unittest.main()
