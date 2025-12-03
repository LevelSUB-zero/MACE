import unittest
from mace.core import action

class TestActionRequest(unittest.TestCase):
    def test_validation(self):
        a = action.ActionRequest("req_1", "test_action", {"p": 1})
        # This should pass if schema allows generic payload or if we strictly check types.
        # The schema for ActionRequest says payload is object.
        
        # We need to ensure schema bundle is available and valid.
        # Assuming generate_schema_bundle was run.
        
        try:
            valid = a.validate()
            self.assertTrue(valid)
        except Exception as e:
            self.fail(f"Validation failed: {e}")

if __name__ == "__main__":
    unittest.main()
