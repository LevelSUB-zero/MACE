import unittest
import os
import json
from mace.memory import semantic
from mace.core import reflective_log, deterministic
from mace.agents import knowledge_agent

class TestFinalAudit(unittest.TestCase):
    
    def setUp(self):
        deterministic.init_seed("audit_seed")
        
    def test_c4_pii_blocking(self):
        """Verify C4: PII Blocking returns 'PRIVACY_BLOCKED'."""
        # CC
        res = semantic.put_sem("user/profile/u/cc", "1234-5678-9999-0000")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "PRIVACY_BLOCKED")
        
        # SSN
        res = semantic.put_sem("user/profile/u/ssn", "123-45-6789")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "PRIVACY_BLOCKED")
        
    def test_e2_immutability(self):
        """Verify E2: Immutability (Amendment Journal)."""
        log_id = "log_test_123"
        entry = {"id": log_id, "data": "original"}
        
        # 1. Amend
        res = reflective_log.amend_log(log_id, {"data": "new"}, "correction")
        self.assertTrue(res["success"])
        
        # 2. Verify file
        found = False
        with open("logs/amendments.jsonl", "r") as f:
            for line in f:
                rec = json.loads(line)
                if rec["original_log_id"] == log_id:
                    self.assertEqual(rec["reason"], "correction")
                    found = True
                    break
        self.assertTrue(found, "Amendment record not found")
        
    def test_g3_knowledge_agent_string(self):
        """Verify G3: Knowledge Agent exact response string."""
        out = knowledge_agent.run({"text": "what is foo"})
        expected = "I don’t have that information stored yet. If you want, tell me and I’ll remember it."
        self.assertEqual(out["text"], expected)

if __name__ == "__main__":
    unittest.main()
