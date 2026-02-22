"""
AdvisoryValidator - Stage-3 Ingestion & Validation

Validates advisory outputs against the Stage-3 rules:
- Schema validation
- Forbidden token blocklist scan
- PII detection
- Signature verification
- Size limits

If validation fails, reject with ADVICE_MALFORMED.

Spec: docs/stage3/advisory_system_spec.md section 7
"""

import re
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from .advisory_output import AdvisoryOutput, AdvisoryType


class ValidationResult(str, Enum):
    """Result of advisory validation."""
    VALID = "valid"
    ADVICE_MALFORMED = "advice_malformed"
    SIGNATURE_INVALID = "signature_invalid"
    FORBIDDEN_TOKEN = "forbidden_token"
    PII_DETECTED = "pii_detected"
    SIZE_EXCEEDED = "size_exceeded"
    SCHEMA_INVALID = "schema_invalid"


@dataclass
class ValidationReport:
    """Result of validating an advisory."""
    result: ValidationResult
    is_valid: bool
    reason_code: str
    reason_details: str
    forbidden_tokens_found: List[str]
    pii_flagged: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result.value,
            "is_valid": self.is_valid,
            "reason_code": self.reason_code,
            "reason_details": self.reason_details,
            "forbidden_tokens_found": self.forbidden_tokens_found,
            "pii_flagged": self.pii_flagged,
        }


# Forbidden tokens per Stage-3 spec
FORBIDDEN_TOKENS = [
    "weight",
    "threshold", 
    "score=",
    "token_budget",
    "promote",
    "write",
    "delete",
    "quarantine",
    "set:",
    "priority=",
    "always",
    "never",
    "autopromote",
    "route_weight",
    "sem_put",
    "apply_patch",
    "deploy",
]

# Forbidden patterns (regex)
FORBIDDEN_PATTERNS = [
    r'"weight"\s*:\s*[\d\.]+',           # JSON weight field
    r'"threshold"\s*:\s*[\d\.]+',        # JSON threshold field
    r'"priority"\s*:\s*[\d]+',           # JSON priority field  
    r'"route_weight"\s*:\s*[\d\.]+',     # JSON route_weight field
    r'"token_budget"\s*:\s*[\d]+',       # JSON token_budget field
    r'score\s*=\s*[\d\.]+',              # score assignment
    r'if\s+.*>\s*[\d\.]+',               # Conditional threshold
    r'<\?',                              # PHP tag
    r'\{%',                              # Template tag
    r'<script',                          # Script tag
]

# PII patterns
PII_PATTERNS = [
    r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',    # Phone numbers
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
    r'\b\d{3}[-]?\d{2}[-]?\d{4}\b',      # SSN
    r'\b(?:password|passwd|pwd)\s*[:=]\s*\S+',  # Passwords
]

# Size limits
MAX_CONTENT_BYTES = 10000  # 10KB max content


class AdvisoryValidator:
    """
    Validates AdvisoryOutput objects against Stage-3 rules.
    
    Validation pipeline:
    1. Schema validation - required fields, types
    2. Forbidden token scan - blocklist check
    3. Pattern scan - regex for forbidden constructs
    4. PII scan - detect and flag PII
    5. Signature verification - HMAC check
    6. Size limits - content byte limit
    """
    
    def __init__(self, custom_forbidden_tokens: Optional[List[str]] = None):
        """Initialize validator with optional custom forbidden tokens."""
        self.forbidden_tokens = FORBIDDEN_TOKENS.copy()
        if custom_forbidden_tokens:
            self.forbidden_tokens.extend(custom_forbidden_tokens)
        
        self.forbidden_patterns = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]
        self.pii_patterns = [re.compile(p, re.IGNORECASE) for p in PII_PATTERNS]
    
    def validate(self, advisory: AdvisoryOutput) -> ValidationReport:
        """
        Run full validation pipeline on advisory.
        
        Returns ValidationReport with detailed results.
        """
        # 1. Schema validation
        schema_result = self._validate_schema(advisory)
        if not schema_result[0]:
            return ValidationReport(
                result=ValidationResult.SCHEMA_INVALID,
                is_valid=False,
                reason_code="SCHEMA_INVALID",
                reason_details=schema_result[1],
                forbidden_tokens_found=[],
                pii_flagged=False,
            )
        
        # 2. Size check
        content_bytes = len(advisory.content.encode('utf-8'))
        if content_bytes > MAX_CONTENT_BYTES:
            return ValidationReport(
                result=ValidationResult.SIZE_EXCEEDED,
                is_valid=False,
                reason_code="SIZE_EXCEEDED",
                reason_details=f"Content size {content_bytes} exceeds limit {MAX_CONTENT_BYTES}",
                forbidden_tokens_found=[],
                pii_flagged=False,
            )
        
        # 3. Forbidden token scan
        content_to_scan = advisory.content.lower()
        if advisory.suggestion_payload:
            content_to_scan += " " + json.dumps(advisory.suggestion_payload).lower()
        
        found_tokens = []
        for token in self.forbidden_tokens:
            if token.lower() in content_to_scan:
                found_tokens.append(token)
        
        if found_tokens:
            return ValidationReport(
                result=ValidationResult.FORBIDDEN_TOKEN,
                is_valid=False,
                reason_code="FORBIDDEN_TOKEN",
                reason_details=f"Found forbidden tokens: {found_tokens}",
                forbidden_tokens_found=found_tokens,
                pii_flagged=False,
            )
        
        # 4. Pattern scan
        for pattern in self.forbidden_patterns:
            if pattern.search(advisory.content):
                return ValidationReport(
                    result=ValidationResult.ADVICE_MALFORMED,
                    is_valid=False,
                    reason_code="FORBIDDEN_PATTERN",
                    reason_details=f"Content matches forbidden pattern: {pattern.pattern}",
                    forbidden_tokens_found=[],
                    pii_flagged=False,
                )
        
        # 5. PII scan (flag but may still accept if redacted)
        pii_flagged = False
        for pattern in self.pii_patterns:
            if pattern.search(advisory.content):
                pii_flagged = True
                break
        
        # 6. Signature verification
        if advisory.immutable_signature:
            if not advisory.verify_signature():
                return ValidationReport(
                    result=ValidationResult.SIGNATURE_INVALID,
                    is_valid=False,
                    reason_code="SIGNATURE_INVALID",
                    reason_details="Immutable signature verification failed",
                    forbidden_tokens_found=[],
                    pii_flagged=pii_flagged,
                )
        
        # All checks passed
        return ValidationReport(
            result=ValidationResult.VALID,
            is_valid=True,
            reason_code="VALID",
            reason_details="Advisory passed all validation checks",
            forbidden_tokens_found=[],
            pii_flagged=pii_flagged,
        )
    
    def _validate_schema(self, advisory: AdvisoryOutput) -> Tuple[bool, str]:
        """Validate required fields and types."""
        # Check required fields
        if not advisory.source_model:
            return False, "Missing required field: source_model"
        if not advisory.job_seed:
            return False, "Missing required field: job_seed"
        if not advisory.content:
            return False, "Missing required field: content"
        
        # Validate advice_type is allowed
        if not isinstance(advisory.advice_type, AdvisoryType):
            try:
                AdvisoryType(advisory.advice_type)
            except ValueError:
                return False, f"Invalid advice_type: {advisory.advice_type}"
        
        return True, "Schema valid"
    
    def validate_batch(self, advisories: List[AdvisoryOutput]) -> List[ValidationReport]:
        """Validate multiple advisories."""
        return [self.validate(a) for a in advisories]


# Convenience function
def validate_advisory(advisory: AdvisoryOutput) -> ValidationReport:
    """Validate a single advisory using default validator."""
    validator = AdvisoryValidator()
    return validator.validate(advisory)


def is_advisory_valid(advisory: AdvisoryOutput) -> bool:
    """Quick check if advisory is valid."""
    return validate_advisory(advisory).is_valid
