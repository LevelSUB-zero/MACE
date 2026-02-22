"""
Schema Lock Validation Tests

Ensures configuration cannot drift from locked values.
Run: python -m pytest tests/schema/test_schema_lock.py -v
"""
import unittest
import os

from mace.config import schema_validator
from mace.config.schema_validator import SchemaViolation


class TestSchemaLock(unittest.TestCase):
    """Verify schema lock is enforced."""
    
    def test_schema_lock_exists(self):
        """Schema lock file must exist."""
        lock_file = os.path.join(
            os.path.dirname(schema_validator.__file__),
            "schema_lock.yaml"
        )
        self.assertTrue(os.path.exists(lock_file), "schema_lock.yaml missing!")
    
    def test_all_validations_pass(self):
        """All current configs must match schema lock."""
        try:
            schema_validator.validate_all()
        except SchemaViolation as e:
            self.fail(f"Schema validation failed:\n{e}")
    
    def test_limits_locked(self):
        """Limits config must match lock."""
        v = schema_validator.get_validator()
        self.assertTrue(v.validate_limits())
    
    def test_stage2_locked(self):
        """Stage-2 config must match lock."""
        v = schema_validator.get_validator()
        self.assertTrue(v.validate_stage2())
    
    def test_containment_invariants(self):
        """Stage-3 containment must be enabled."""
        v = schema_validator.get_validator()
        self.assertTrue(v.validate_stage3_containment())
    
    def test_learning_modes(self):
        """Learning modes must be valid."""
        v = schema_validator.get_validator()
        self.assertTrue(v.validate_learning_mode())
    
    def test_lock_hash_exists(self):
        """Lock hash should be computable."""
        hash_val = schema_validator.get_lock_hash()
        self.assertEqual(len(hash_val), 64)  # SHA256 hex
        print(f"Schema lock hash: {hash_val}")


if __name__ == "__main__":
    unittest.main()
