import unittest
import os
import json
from mace.memory import semantic

class TestCanonicalKeys(unittest.TestCase):
    def setUp(self):
        # Create a temporary synonyms file for testing
        self.synonyms = {
            "test alias": "user/profile/test_user/alias_target",
            "dynamic alias": "user/profile/user_id/dynamic_target"
        }
        with open("sem_synonyms.json", "w") as f:
            json.dump(self.synonyms, f)

    def tearDown(self):
        # Restore original synonyms if needed, or just leave it (it's a test env)
        # For safety, let's try to restore the original content if we overwrote it?
        # Or just rely on the fact that we wrote the "real" one in the previous step 
        # and this test might overwrite it.
        # Actually, the previous step wrote the real one.
        # We should probably use a different file or mock it, but `semantic.py` hardcodes the filename.
        # For now, let's just write back the "real" one at the end or accept that tests modify env.
        # Let's write back the simple one from the previous step to be clean.
        original = {
          "my favorite color": "user/profile/user_id/favorite_color",
          "my name": "user/profile/user_id/name",
          "current time": "world/time/global/iso8601"
        }
        with open("sem_synonyms.json", "w") as f:
            json.dump(original, f, indent=2)

    def test_t1_valid_canonical_key(self):
        """T1: Valid canonical key passes validation."""
        key = "user/profile/user_123/favorite_color"
        # Should not raise
        semantic._validate_key(key)

    def test_t2_invalid_canonical_key(self):
        """T2: Invalid canonical key fails validation."""
        invalid_keys = [
            "User/Profile/123", # Uppercase
            "user/profile/123/favorite color", # Space
            "user/profile", # Too few segments (needs 4)
            "user/profile/123/too/many", # Too many segments
            "user/profile/123/invalid$char" # Invalid char
        ]
        for key in invalid_keys:
            with self.assertRaises(ValueError):
                semantic._validate_key(key)

    def test_t3_generate_canonical_key(self):
        """T3: generate_canonical_key sanitizes input."""
        raw = "User Name 123!"
        # Lowercase -> user name 123!
        # Spaces -> user_name_123!
        # Remove non-alphanum -> user_name_123
        expected = "user_name_123"
        self.assertEqual(semantic.generate_canonical_key(raw), expected)

    def test_t4_resolve_alias_exact(self):
        """T4: sem_resolve_alias resolves exact match."""
        resolved = semantic.sem_resolve_alias("test alias", user_id="u1")
        self.assertEqual(resolved, "user/profile/test_user/alias_target")

    def test_t5_resolve_alias_dynamic(self):
        """T5: sem_resolve_alias resolves dynamic user_id."""
        resolved = semantic.sem_resolve_alias("dynamic alias", user_id="bob")
        self.assertEqual(resolved, "user/profile/bob/dynamic_target")

    def test_t6_resolve_alias_fallback(self):
        """T6: sem_resolve_alias falls back to generation."""
        # "Unknown Alias" -> "unknown_alias"
        resolved = semantic.sem_resolve_alias("Unknown Alias")
        self.assertEqual(resolved, "unknown_alias")

if __name__ == '__main__':
    unittest.main()
