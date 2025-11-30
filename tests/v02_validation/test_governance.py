import unittest
import os
import json
from mace.memory import semantic
from mace.governance import amendment

from mace.core import deterministic

class TestGovernance(unittest.TestCase):
    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")
        deterministic.init_seed("gov_test_seed")
        
        # Create dummy amendments file
        self.amendments = [
            {
                "amendment_id": "amd_1",
                "policy_type": "block_key",
                "target": "user/profile/test/banned_key",
                "active": True,
                "created_at": "2023-01-01T00:00:00Z"
            },
            {
                "amendment_id": "amd_2",
                "policy_type": "block_key",
                "target": "user/profile/test/inactive_ban",
                "active": False,
                "created_at": "2023-01-01T00:00:00Z"
            }
        ]
        with open("amendments.jsonl", "w") as f:
            for amd in self.amendments:
                f.write(json.dumps(amd) + "\n")

    def tearDown(self):
        if os.path.exists("amendments.jsonl"):
            os.remove("amendments.jsonl")
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")

    def test_load_amendments(self):
        """Verify loading."""
        loaded = amendment.load_amendments()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["amendment_id"], "amd_1")

    def test_policy_check(self):
        """Verify check_policy logic."""
        self.assertTrue(amendment.check_policy("block_key", "user/profile/test/banned_key"))
        self.assertFalse(amendment.check_policy("block_key", "user/profile/test/inactive_ban"))
        self.assertFalse(amendment.check_policy("block_key", "user/profile/test/allowed_key"))

    def test_put_sem_blocked(self):
        """Verify put_sem enforces block_key."""
        # Blocked key
        res = semantic.put_sem("user/profile/test/banned_key", "value")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "POLICY_BLOCKED")
        
        # Allowed key
        res = semantic.put_sem("user/profile/test/allowed_key", "value")
        if not res["success"]:
            print(f"DEBUG: Allowed key failed: {res}")
        self.assertTrue(res["success"])

if __name__ == '__main__':
    unittest.main()
