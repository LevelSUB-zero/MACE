import unittest
from mace.core import reflective_log

class TestLogSecurity(unittest.TestCase):
    
    def test_sign_and_verify(self):
        entry = {
            "log_id": "log_123",
            "percept": {"text": "hello"},
            "random_seed": "seed_123"
        }
        secret = "my_secret_key"
        
        # Sign
        signed_entry = reflective_log.sign_log_entry(entry, secret)
        self.assertIn("signature", signed_entry)
        
        # Verify
        self.assertTrue(reflective_log.verify_log_entry(signed_entry, secret))
        
    def test_tamper_detection(self):
        entry = {
            "log_id": "log_123",
            "percept": {"text": "hello"}
        }
        secret = "my_secret_key"
        
        signed_entry = reflective_log.sign_log_entry(entry, secret)
        
        # Tamper
        signed_entry["percept"]["text"] = "hacked"
        
        # Verify
        self.assertFalse(reflective_log.verify_log_entry(signed_entry, secret))
        
    def test_wrong_key(self):
        entry = {"log_id": "log_123"}
        secret = "key1"
        wrong_secret = "key2"
        
        signed_entry = reflective_log.sign_log_entry(entry, secret)
        self.assertFalse(reflective_log.verify_log_entry(signed_entry, wrong_secret))

if __name__ == "__main__":
    unittest.main()
