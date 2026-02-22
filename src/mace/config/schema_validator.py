"""
Schema Lock Validator

Enforces frozen configuration values from schema_lock.yaml.
Run at startup or in CI to detect configuration drift.

Usage:
    from mace.config import schema_validator
    schema_validator.validate_all()  # Raises SchemaViolation on drift
"""
import os
import yaml
import hashlib
from typing import Dict, Any, List, Optional


class SchemaViolation(Exception):
    """Raised when configuration diverges from locked schema."""
    pass


class SchemaValidator:
    """Validates current config against frozen schema lock."""
    
    def __init__(self):
        self.config_dir = os.path.dirname(__file__)
        self.lock_file = os.path.join(self.config_dir, "schema_lock.yaml")
        self._lock_data: Optional[Dict] = None
        self._violations: List[str] = []
    
    @property
    def lock_data(self) -> Dict:
        if self._lock_data is None:
            if not os.path.exists(self.lock_file):
                raise SchemaViolation("schema_lock.yaml not found - cannot validate")
            with open(self.lock_file, 'r') as f:
                self._lock_data = yaml.safe_load(f)
        return self._lock_data
    
    def _load_yaml(self, filename: str) -> Dict:
        filepath = os.path.join(self.config_dir, filename)
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r') as f:
            return yaml.safe_load(f) or {}
    
    def _check_value(self, path: str, expected: Any, actual: Any) -> bool:
        """Check if a value matches expected. Returns True if OK."""
        if expected != actual:
            self._violations.append(
                f"SCHEMA DRIFT: {path}\n"
                f"  Expected: {expected}\n"
                f"  Actual:   {actual}"
            )
            return False
        return True
    
    def validate_limits(self) -> bool:
        """Validate limits.yaml against schema lock."""
        actual = self._load_yaml("limits.yaml")
        expected = self.lock_data.get("limits", {})
        
        all_ok = True
        for key, val in expected.items():
            if key not in actual:
                self._violations.append(f"MISSING: limits.{key}")
                all_ok = False
            elif not self._check_value(f"limits.{key}", val, actual[key]):
                all_ok = False
        
        return all_ok
    
    def validate_stage2(self) -> bool:
        """Validate stage2.yaml against schema lock."""
        actual = self._load_yaml("stage2.yaml")
        expected = self.lock_data.get("stage2", {})
        
        all_ok = True
        for key, val in expected.items():
            actual_val = actual.get(key)
            if not self._check_value(f"stage2.{key}", val, actual_val):
                all_ok = False
        
        return all_ok
    
    def validate_stage3_containment(self) -> bool:
        """Validate Stage-3 containment invariants are enabled."""
        actual = self._load_yaml("stage3.yaml")
        
        invariants = [
            ("TEMPORAL_CONTAINMENT", True),
            ("PERSISTENCE_CONTAINMENT", True),
            ("SEMANTIC_CONTAINMENT", True),
            ("INTERPRETABILITY_LOCK", True),
        ]
        
        all_ok = True
        for key, expected in invariants:
            if actual.get(key) != expected:
                self._violations.append(
                    f"CONTAINMENT BROKEN: stage3.{key} must be {expected}"
                )
                all_ok = False
        
        return all_ok
    
    def validate_learning_mode(self) -> bool:
        """Validate learning modes are correct for each stage."""
        stage2 = self._load_yaml("stage2.yaml")
        stage3 = self._load_yaml("stage3.yaml")
        
        all_ok = True
        
        # Stage-2 MUST be shadow
        if stage2.get("MEM_LEARNING_MODE") != "shadow":
            self._violations.append(
                "LEARNING MODE VIOLATION: stage2.MEM_LEARNING_MODE must be 'shadow'"
            )
            all_ok = False
        
        # Stage-3 can be shadow or advisory
        if stage3.get("MEM_LEARNING_MODE") not in ("shadow", "advisory"):
            self._violations.append(
                "LEARNING MODE VIOLATION: stage3.MEM_LEARNING_MODE must be 'shadow' or 'advisory'"
            )
            all_ok = False
        
        return all_ok
    
    def validate_all(self) -> bool:
        """Run all validations. Raises SchemaViolation if any fail."""
        self._violations = []
        
        checks = [
            ("limits", self.validate_limits),
            ("stage2", self.validate_stage2),
            ("stage3_containment", self.validate_stage3_containment),
            ("learning_mode", self.validate_learning_mode),
        ]
        
        all_ok = True
        for name, check_fn in checks:
            try:
                if not check_fn():
                    all_ok = False
            except Exception as e:
                self._violations.append(f"VALIDATION ERROR in {name}: {e}")
                all_ok = False
        
        if not all_ok:
            msg = "SCHEMA LOCK VIOLATIONS DETECTED:\n\n" + "\n\n".join(self._violations)
            raise SchemaViolation(msg)
        
        return True
    
    def get_lock_hash(self) -> str:
        """Get SHA256 hash of the schema lock file."""
        with open(self.lock_file, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def get_violations(self) -> List[str]:
        """Get list of violations from last validation."""
        return self._violations.copy()


# Module-level validator instance
_validator: Optional[SchemaValidator] = None


def get_validator() -> SchemaValidator:
    global _validator
    if _validator is None:
        _validator = SchemaValidator()
    return _validator


def validate_all() -> bool:
    """Validate all configurations against schema lock."""
    return get_validator().validate_all()


def get_lock_hash() -> str:
    """Get hash of the schema lock for verification."""
    return get_validator().get_lock_hash()


def assert_schema_integrity():
    """Assert schema integrity at startup. Raises on failure."""
    try:
        validate_all()
        print(f"[SCHEMA] ✓ Configuration locked (hash: {get_lock_hash()[:16]}...)")
    except SchemaViolation as e:
        print(f"[SCHEMA] ✗ DRIFT DETECTED")
        raise
