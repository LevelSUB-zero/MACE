"""
Containment Layer - P2 Informational Sealing

This module enforces strict informational containment:
- Advisory entropy & format invariants
- Metadata redaction
- Timing normalization
- Divergence representation limits
- No learning, no adaptation enforcement

Purpose: Even if advisory is ignored causally, future components will read these artifacts.
Containment ensures information cannot leak sideways or act as covert channels.

Principle: Answer what exists before who decides.
"""

import re
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


# =============================================================================
# P2.5: ADVISORY ENTROPY & FORMAT INVARIANTS
# =============================================================================

@dataclass(frozen=True)
class AdvisoryFormatConstraints:
    """
    Immutable format constraints for advisory content.
    These prevent advisory from becoming a covert channel.
    """
    # Length constraints
    min_content_length: int = 10
    max_content_length: int = 500
    
    # Evidence constraints
    max_evidence_refs: int = 10
    max_evidence_ref_length: int = 64
    
    # Payload constraints
    max_payload_keys: int = 10
    max_payload_value_length: int = 200
    
    # Confidence constraints (only allowed values)
    allowed_confidence_values: Tuple[str, ...] = ("low", "medium", "high", "uncertain")
    
    # Forbidden content patterns (prevent embedding data)
    forbidden_patterns: Tuple[str, ...] = (
        r'[a-zA-Z0-9+/]{40,}={0,2}',  # Base64-like
        r'0x[a-fA-F0-9]{16,}',         # Long hex
        r'\d{10,}',                     # Long numbers (>10 digits)
    )


# Default constraints (immutable)
DEFAULT_CONSTRAINTS = AdvisoryFormatConstraints()


class ContainmentViolation(Exception):
    """Raised when containment is violated."""
    pass


def enforce_advisory_format(
    content: str,
    evidence_refs: List[str],
    suggestion_payload: Dict[str, Any],
    confidence: str,
    constraints: AdvisoryFormatConstraints = DEFAULT_CONSTRAINTS
) -> Tuple[bool, List[str]]:
    """
    Enforce format constraints on advisory.
    
    Returns (is_valid, list_of_violations).
    """
    violations = []
    
    # Length constraints
    if len(content) < constraints.min_content_length:
        violations.append(f"content_too_short:{len(content)}<{constraints.min_content_length}")
    if len(content) > constraints.max_content_length:
        violations.append(f"content_too_long:{len(content)}>{constraints.max_content_length}")
    
    # Evidence constraints
    if len(evidence_refs) > constraints.max_evidence_refs:
        violations.append(f"too_many_evidence_refs:{len(evidence_refs)}>{constraints.max_evidence_refs}")
    for ref in evidence_refs:
        if len(ref) > constraints.max_evidence_ref_length:
            violations.append(f"evidence_ref_too_long:{len(ref)}>{constraints.max_evidence_ref_length}")
    
    # Payload constraints
    if len(suggestion_payload) > constraints.max_payload_keys:
        violations.append(f"too_many_payload_keys:{len(suggestion_payload)}>{constraints.max_payload_keys}")
    for key, value in suggestion_payload.items():
        if isinstance(value, str) and len(value) > constraints.max_payload_value_length:
            violations.append(f"payload_value_too_long:{key}:{len(value)}>{constraints.max_payload_value_length}")
    
    # Confidence constraints
    if confidence.lower() not in constraints.allowed_confidence_values:
        violations.append(f"invalid_confidence:{confidence}")
    
    # Forbidden patterns (prevent embedding data)
    for pattern in constraints.forbidden_patterns:
        if re.search(pattern, content):
            violations.append(f"forbidden_pattern:{pattern}")
        for ref in evidence_refs:
            if re.search(pattern, ref):
                violations.append(f"forbidden_pattern_in_ref:{pattern}")
    
    return (len(violations) == 0, violations)


def normalize_advisory_content(content: str, max_length: int = 500) -> str:
    """
    Normalize advisory content:
    - Trim whitespace
    - Collapse multiple spaces
    - Truncate to max length
    - Remove non-printable characters
    """
    # Remove non-printable characters
    content = ''.join(c for c in content if c.isprintable() or c in '\n\t')
    
    # Collapse multiple spaces
    content = re.sub(r' +', ' ', content)
    
    # Collapse multiple newlines
    content = re.sub(r'\n+', '\n', content)
    
    # Trim
    content = content.strip()
    
    # Truncate
    if len(content) > max_length:
        content = content[:max_length-3] + "..."
    
    return content


# =============================================================================
# P2.6: METADATA REDACTION LAYER
# =============================================================================

@dataclass(frozen=True)
class RedactionPolicy:
    """
    Defines what metadata is NEVER persisted.
    """
    # Raw numeric scores (only textual labels allowed)
    redact_raw_scores: bool = True
    
    # Token-level rationale
    redact_token_rationale: bool = True
    
    # Timing deltas between operations
    redact_timing_deltas: bool = True
    
    # Full candidate lists (only selected)
    redact_candidate_lists: bool = True
    
    # Internal model states
    redact_model_states: bool = True
    
    # Keys that should be redacted
    redacted_keys: Tuple[str, ...] = (
        "raw_score",
        "numeric_score",
        "logit",
        "probability",
        "timing_ms",
        "latency_ns",
        "candidates",
        "all_candidates",
        "hidden_state",
        "internal_state",
        "weight",
        "gradient",
        "loss",
    )


DEFAULT_REDACTION_POLICY = RedactionPolicy()


def redact_metadata(
    data: Dict[str, Any],
    policy: RedactionPolicy = DEFAULT_REDACTION_POLICY
) -> Dict[str, Any]:
    """
    Redact sensitive metadata from dictionary.
    Returns a new dictionary with redacted values.
    """
    redacted = {}
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # Check if key should be redacted
        should_redact = any(
            redacted_key in key_lower 
            for redacted_key in policy.redacted_keys
        )
        
        if should_redact:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            # Recursively redact nested dicts
            redacted[key] = redact_metadata(value, policy)
        elif isinstance(value, list) and key_lower in ("candidates", "all_candidates"):
            # Redact candidate lists entirely
            redacted[key] = "[REDACTED_LIST]"
        else:
            redacted[key] = value
    
    return redacted


def redact_advisory_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Redact advisory suggestion payload."""
    return redact_metadata(payload, DEFAULT_REDACTION_POLICY)


# =============================================================================
# P2.7: TIMING & ORDERING NORMALIZATION
# =============================================================================

def normalize_timestamp(timestamp: str) -> str:
    """
    Normalize timestamp to remove sub-second precision.
    This prevents timing side-channels.
    
    Input: "2026-01-24T12:34:56.789123"
    Output: "2026-01-24T12:34:56Z"
    """
    # Parse and reformat without microseconds
    try:
        if '.' in timestamp:
            base = timestamp.split('.')[0]
        elif '+' in timestamp:
            base = timestamp.split('+')[0]
        else:
            base = timestamp.rstrip('Z')
        
        # Ensure UTC suffix
        return base + "Z"
    except Exception:
        return timestamp


def normalize_event_ordering(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize event ordering to be deterministic.
    Sort by (job_seed, event_type, event_id).
    
    This prevents ordering from becoming a covert channel.
    """
    def sort_key(event: Dict[str, Any]) -> tuple:
        return (
            event.get("job_seed", ""),
            event.get("event_type", ""),
            event.get("event_id", ""),
        )
    
    return sorted(events, key=sort_key)


def strip_timing_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strip all timing-related metadata.
    """
    timing_keys = {
        "created_at", "updated_at", "timestamp", "time", 
        "start_time", "end_time", "duration", "latency"
    }
    
    result = {}
    for key, value in data.items():
        if key.lower() in timing_keys:
            # Replace with normalized version or redact
            if "at" in key.lower() or "time" in key.lower():
                if isinstance(value, str):
                    result[key] = normalize_timestamp(value)
                else:
                    result[key] = "[NORMALIZED]"
            else:
                result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = strip_timing_metadata(value)
        else:
            result[key] = value
    
    return result


# =============================================================================
# P2.8: DIVERGENCE REPRESENTATION LIMITS
# =============================================================================

class DivergenceRepresentation(str, Enum):
    """
    Allowed divergence representations.
    These are CATEGORICAL, not continuous.
    No numeric scores allowed.
    """
    NO_DIVERGENCE = "no_divergence"
    ROUTE_IGNORED = "route_ignored"
    PREDICTION_WRONG = "prediction_wrong"
    COUNCIL_DISAGREED = "council_disagreed"
    REPLAY_DIVERGENCE = "replay_divergence"


class ImpactCategory(str, Enum):
    """
    Impact categories - TEXTUAL ONLY.
    No numeric values allowed.
    """
    NEGLIGIBLE = "negligible"
    MINOR = "minor"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"


def validate_divergence_representation(
    divergence_type: str,
    impact_estimate: str
) -> Tuple[bool, List[str]]:
    """
    Validate divergence representation is within allowed categories.
    """
    violations = []
    
    # Check divergence type
    allowed_types = {e.value for e in DivergenceRepresentation}
    if divergence_type not in allowed_types:
        violations.append(f"invalid_divergence_type:{divergence_type}")
    
    # Check impact estimate
    allowed_impacts = {e.value for e in ImpactCategory}
    if impact_estimate not in allowed_impacts:
        violations.append(f"invalid_impact_estimate:{impact_estimate}")
    
    return (len(violations) == 0, violations)


def quantize_to_category(value: float, thresholds: List[float] = None) -> str:
    """
    Quantize numeric value to categorical bucket.
    This prevents numeric information leakage.
    
    Default thresholds: [0.25, 0.5, 0.75]
    """
    if thresholds is None:
        thresholds = [0.25, 0.5, 0.75]
    
    if value < thresholds[0]:
        return "negligible"
    elif value < thresholds[1]:
        return "minor"
    elif value < thresholds[2]:
        return "moderate"
    else:
        return "significant"


# =============================================================================
# P2.9: NO LEARNING, NO ADAPTATION ENFORCEMENT
# =============================================================================

class AdaptationAttempt(Exception):
    """Raised when adaptation is detected."""
    pass


# Forbidden patterns that indicate learning/adaptation
FORBIDDEN_ADAPTATION_PATTERNS = [
    # Weight/parameter updates
    r'update.*weight',
    r'weight.*update',
    r'modify.*parameter',
    r'adjust.*threshold',
    r'learn.*from',
    r'adapt.*to',
    r'train.*on',
    r'optimize.*for',
    
    # Feedback loops
    r'feedback.*loop',
    r'reinforce',
    r'backprop',
    r'gradient',
    
    # Self-modification
    r'self.*modify',
    r'auto.*improve',
    r'evolve',
    r'mutate',
]


def check_for_adaptation_attempt(
    code_or_content: str,
    raise_on_violation: bool = True
) -> Tuple[bool, List[str]]:
    """
    Check if content contains adaptation/learning patterns.
    
    This is a static analysis check to prevent learning code from sneaking in.
    """
    violations = []
    content_lower = code_or_content.lower()
    
    for pattern in FORBIDDEN_ADAPTATION_PATTERNS:
        if re.search(pattern, content_lower):
            violations.append(f"adaptation_pattern:{pattern}")
    
    if violations and raise_on_violation:
        raise AdaptationAttempt(f"Adaptation attempt detected: {violations}")
    
    return (len(violations) == 0, violations)


def validate_no_numeric_feedback(
    observation: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Validate that observation contains no numeric feedback that could drive learning.
    """
    violations = []
    
    # Check for numeric values that could be used as rewards/losses
    feedback_keys = {"reward", "loss", "score", "error", "accuracy", "metric"}
    
    for key, value in observation.items():
        key_lower = key.lower()
        
        # Check if key suggests feedback signal
        if any(fb in key_lower for fb in feedback_keys):
            if isinstance(value, (int, float)):
                violations.append(f"numeric_feedback:{key}={value}")
    
    return (len(violations) == 0, violations)


# =============================================================================
# CONTAINMENT VALIDATOR (COMBINES ALL CHECKS)
# =============================================================================

@dataclass
class ContainmentReport:
    """Report from containment validation."""
    is_contained: bool
    format_violations: List[str] = field(default_factory=list)
    redaction_applied: bool = False
    timing_normalized: bool = False
    divergence_valid: bool = True
    adaptation_check_passed: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_contained": self.is_contained,
            "format_violations": self.format_violations,
            "redaction_applied": self.redaction_applied,
            "timing_normalized": self.timing_normalized,
            "divergence_valid": self.divergence_valid,
            "adaptation_check_passed": self.adaptation_check_passed,
        }


def validate_containment(
    content: str,
    evidence_refs: List[str],
    suggestion_payload: Dict[str, Any],
    confidence: str,
    divergence_type: str = None,
    impact_estimate: str = None,
) -> ContainmentReport:
    """
    Full containment validation.
    
    Combines all P2 checks.
    """
    report = ContainmentReport(is_contained=True)
    
    # P2.5: Format validation
    format_ok, format_violations = enforce_advisory_format(
        content, evidence_refs, suggestion_payload, confidence
    )
    if not format_ok:
        report.format_violations = format_violations
        report.is_contained = False
    
    # P2.8: Divergence validation
    if divergence_type and impact_estimate:
        div_ok, div_violations = validate_divergence_representation(
            divergence_type, impact_estimate
        )
        if not div_ok:
            report.divergence_valid = False
            report.format_violations.extend(div_violations)
            report.is_contained = False
    
    # P2.9: Adaptation check
    adapt_ok, adapt_violations = check_for_adaptation_attempt(
        content, raise_on_violation=False
    )
    if not adapt_ok:
        report.adaptation_check_passed = False
        report.format_violations.extend(adapt_violations)
        report.is_contained = False
    
    return report


def apply_containment(
    content: str,
    evidence_refs: List[str],
    suggestion_payload: Dict[str, Any],
    timestamp: str = None,
) -> Tuple[str, List[str], Dict[str, Any], str]:
    """
    Apply containment transformations:
    - Normalize content
    - Redact payload
    - Normalize timestamp
    
    Returns: (normalized_content, normalized_refs, redacted_payload, normalized_timestamp)
    """
    # Normalize content
    normalized_content = normalize_advisory_content(content)
    
    # Normalize evidence refs (length limit)
    normalized_refs = [
        ref[:DEFAULT_CONSTRAINTS.max_evidence_ref_length] 
        for ref in evidence_refs[:DEFAULT_CONSTRAINTS.max_evidence_refs]
    ]
    
    # Redact payload
    redacted_payload = redact_advisory_payload(suggestion_payload)
    
    # Normalize timestamp
    normalized_timestamp = normalize_timestamp(timestamp) if timestamp else None
    
    return (normalized_content, normalized_refs, redacted_payload, normalized_timestamp)
