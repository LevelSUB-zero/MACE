import unittest
import json
from mace.core import deterministic, canonical, signing, codec

class TestDeterministicPrimitives(unittest.TestCase):
    
    def test_canonical_serialization(self):
        """Verify canonical JSON serialization rules."""
        obj = {
            "b": 2,
            "a": 1,
            "c": [3.1415926535, "hello"],
            "d": {"x": "y"}
        }
        
        # Expected: sorted keys, no whitespace, 9-decimal float
        # 3.1415926535 -> 3.141592654
        expected = '{"a":1,"b":2,"c":[3.141592654,"hello"],"d":{"x":"y"}}'
        
        serialized = canonical.canonical_json_serialize(obj)
        self.assertEqual(serialized, expected)
        
        # Verify codec wrapper
        self.assertEqual(codec.encode(obj), expected)
        
    def test_canonical_float(self):
        """Verify float formatting."""
        self.assertEqual(canonical.canonical_float_format(1.0/3), "0.333333333")
        self.assertEqual(canonical.canonical_float_format(1.5), "1.500000000")
        
    def test_canonical_key(self):
        """Verify key normalization."""
        raw = " User / Profile / Name "
        expected = "user/profile/name"
        self.assertEqual(canonical.canonical_key(raw), expected)
        
        # Special chars allowed: _ . : / -
        raw2 = "Namespace:Key-Value_1.0"
        expected2 = "namespace:key-value_1.0"
        self.assertEqual(canonical.canonical_key(raw2), expected2)
        
    def test_deterministic_id(self):
        """Verify deterministic ID generation."""
        deterministic.init_seed("test_seed")
        
        id1 = deterministic.deterministic_id("test", "payload1")
        
        deterministic.init_seed("test_seed")
        id2 = deterministic.deterministic_id("test", "payload1")
        
        self.assertEqual(id1, id2)
        
        # Different payload
        id3 = deterministic.deterministic_id("test", "payload2")
        self.assertNotEqual(id1, id3)
        
    def test_signing(self):
        """Verify HMAC signing."""
        payload = {"foo": "bar"}
        key_id = "test-key"
        
        sig = signing.sign_payload(payload, key_id)
        
        # Verify valid
        self.assertTrue(signing.verify_signature(payload, sig, key_id))
        
        # Verify invalid signature
        self.assertFalse(signing.verify_signature(payload, "invalid_sig", key_id))
        
        # Verify tampered payload
        payload_tampered = {"foo": "baz"}
        self.assertFalse(signing.verify_signature(payload_tampered, sig, key_id))
        
        # Verify wrong key
        self.assertFalse(signing.verify_signature(payload, sig, "wrong-key"))

if __name__ == "__main__":
    unittest.main()
