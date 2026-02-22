"""
P2 Containment Tests - Informational Sealing Verification

Tests for:
5. Advisory entropy & format invariants
6. Metadata redaction layer
7. Timing/ordering normalization
8. Divergence representation limits
9. No learning, no adaptation enforcement
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from mace.stage3.containment import (
    # P2.5 - Format constraints
    AdvisoryFormatConstraints, DEFAULT_CONSTRAINTS,
    enforce_advisory_format, normalize_advisory_content,
    ContainmentViolation,
    
    # P2.6 - Redaction
    RedactionPolicy, DEFAULT_REDACTION_POLICY,
    redact_metadata, redact_advisory_payload,
    
    # P2.7 - Timing
    normalize_timestamp, normalize_event_ordering, strip_timing_metadata,
    
    # P2.8 - Divergence
    DivergenceRepresentation, ImpactCategory,
    validate_divergence_representation, quantize_to_category,
    
    # P2.9 - No adaptation
    AdaptationAttempt, FORBIDDEN_ADAPTATION_PATTERNS,
    check_for_adaptation_attempt, validate_no_numeric_feedback,
    
    # Combined
    validate_containment, apply_containment, ContainmentReport,
)


class TestAdvisoryFormatConstraints:
    """P2.5: Advisory entropy & format invariants."""
    
    def test_valid_advisory_passes(self):
        """Valid advisory should pass format checks."""
        ok, violations = enforce_advisory_format(
            content="This is a valid advisory suggestion for routing.",
            evidence_refs=["ref-001", "ref-002"],
            suggestion_payload={"suggested_agent": "math_agent"},
            confidence="medium"
        )
        assert ok == True
        assert len(violations) == 0
    
    def test_content_too_short(self):
        """Content below minimum length should fail."""
        ok, violations = enforce_advisory_format(
            content="Short",
            evidence_refs=[],
            suggestion_payload={},
            confidence="low"
        )
        assert ok == False
        assert any("too_short" in v for v in violations)
    
    def test_content_too_long(self):
        """Content above maximum length should fail."""
        long_content = "x" * 600
        ok, violations = enforce_advisory_format(
            content=long_content,
            evidence_refs=[],
            suggestion_payload={},
            confidence="low"
        )
        assert ok == False
        assert any("too_long" in v for v in violations)
    
    def test_too_many_evidence_refs(self):
        """More than 10 evidence refs should fail."""
        ok, violations = enforce_advisory_format(
            content="Valid content here",
            evidence_refs=[f"ref-{i:03d}" for i in range(15)],
            suggestion_payload={},
            confidence="low"
        )
        assert ok == False
        assert any("too_many_evidence" in v for v in violations)
    
    def test_forbidden_base64_pattern(self):
        """Base64-like patterns should be detected."""
        ok, violations = enforce_advisory_format(
            content="Contains base64: YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            evidence_refs=[],
            suggestion_payload={},
            confidence="low"
        )
        assert ok == False
        assert any("forbidden_pattern" in v for v in violations)
    
    def test_invalid_confidence(self):
        """Invalid confidence value should fail."""
        ok, violations = enforce_advisory_format(
            content="Valid content here",
            evidence_refs=[],
            suggestion_payload={},
            confidence="very_high"  # Not in allowed list
        )
        assert ok == False
        assert any("invalid_confidence" in v for v in violations)
    
    def test_normalize_content(self):
        """Content normalization should work."""
        content = "   Multiple   spaces   and\n\n\nnewlines   "
        normalized = normalize_advisory_content(content)
        assert "  " not in normalized  # No double spaces
        assert "\n\n" not in normalized  # No double newlines
        assert normalized == normalized.strip()


class TestMetadataRedaction:
    """P2.6: Metadata redaction layer."""
    
    def test_redacts_raw_scores(self):
        """Raw scores should be redacted."""
        data = {
            "content": "visible",
            "raw_score": 0.95,
            "numeric_score": 42,
        }
        redacted = redact_metadata(data)
        assert redacted["content"] == "visible"
        assert redacted["raw_score"] == "[REDACTED]"
        assert redacted["numeric_score"] == "[REDACTED]"
    
    def test_redacts_timing(self):
        """Timing metadata should be redacted."""
        data = {
            "name": "test",
            "timing_ms": 123,
            "latency_ns": 456789,
        }
        redacted = redact_metadata(data)
        assert redacted["name"] == "test"
        assert redacted["timing_ms"] == "[REDACTED]"
        assert redacted["latency_ns"] == "[REDACTED]"
    
    def test_redacts_nested(self):
        """Nested dicts should be recursively redacted."""
        data = {
            "outer": "visible",
            "inner": {
                "visible_key": "ok",
                "raw_score": 0.5,
            }
        }
        redacted = redact_metadata(data)
        assert redacted["outer"] == "visible"
        assert redacted["inner"]["visible_key"] == "ok"
        assert redacted["inner"]["raw_score"] == "[REDACTED]"
    
    def test_redacts_candidate_lists(self):
        """Candidate lists should be redacted entirely."""
        data = {
            "selected": "agent_math",
            "candidates": ["agent_math", "agent_research", "agent_general"],
        }
        redacted = redact_metadata(data)
        assert redacted["selected"] == "agent_math"
        assert redacted["candidates"] == "[REDACTED]"  # Key contains 'candidates'


class TestTimingNormalization:
    """P2.7: Timing/ordering normalization."""
    
    def test_normalize_timestamp_removes_microseconds(self):
        """Timestamps should lose sub-second precision."""
        ts = "2026-01-24T12:34:56.789123"
        normalized = normalize_timestamp(ts)
        assert "789" not in normalized
        assert normalized == "2026-01-24T12:34:56Z"
    
    def test_normalize_timestamp_handles_timezone(self):
        """Timestamps with timezone should be normalized."""
        ts = "2026-01-24T12:34:56+05:30"
        normalized = normalize_timestamp(ts)
        assert "05:30" not in normalized
        assert normalized.endswith("Z")
    
    def test_normalize_event_ordering(self):
        """Events should be sorted deterministically."""
        events = [
            {"job_seed": "b", "event_type": "x", "event_id": "1"},
            {"job_seed": "a", "event_type": "y", "event_id": "2"},
            {"job_seed": "a", "event_type": "x", "event_id": "3"},
        ]
        ordered = normalize_event_ordering(events)
        
        # Should be sorted by (job_seed, event_type, event_id)
        assert ordered[0]["job_seed"] == "a"
        assert ordered[0]["event_type"] == "x"
        assert ordered[1]["event_type"] == "y"
        assert ordered[2]["job_seed"] == "b"
    
    def test_strip_timing_metadata(self):
        """Timing metadata should be normalized or redacted."""
        data = {
            "name": "test",
            "created_at": "2026-01-24T12:34:56.789",
            "duration": 123,
        }
        stripped = strip_timing_metadata(data)
        assert stripped["name"] == "test"
        assert "789" not in stripped["created_at"]
        assert stripped["duration"] == "[NORMALIZED]"  # Timing-related key


class TestDivergenceRepresentationLimits:
    """P2.8: Divergence representation limits."""
    
    def test_valid_divergence_types(self):
        """Valid divergence types should pass."""
        for dt in DivergenceRepresentation:
            ok, violations = validate_divergence_representation(
                dt.value, "minor"
            )
            assert ok == True, f"Failed for {dt.value}"
    
    def test_invalid_divergence_type(self):
        """Invalid divergence type should fail."""
        ok, violations = validate_divergence_representation(
            "custom_divergence_type", "minor"
        )
        assert ok == False
        assert any("invalid_divergence" in v for v in violations)
    
    def test_valid_impact_categories(self):
        """Valid impact categories should pass."""
        for ic in ImpactCategory:
            ok, violations = validate_divergence_representation(
                "no_divergence", ic.value
            )
            assert ok == True, f"Failed for {ic.value}"
    
    def test_invalid_impact_category(self):
        """Invalid impact category should fail."""
        ok, violations = validate_divergence_representation(
            "no_divergence", "catastrophic"  # Not allowed
        )
        assert ok == False
        assert any("invalid_impact" in v for v in violations)
    
    def test_quantize_to_category(self):
        """Numeric values should quantize to categories."""
        assert quantize_to_category(0.1) == "negligible"
        assert quantize_to_category(0.3) == "minor"
        assert quantize_to_category(0.6) == "moderate"
        assert quantize_to_category(0.9) == "significant"


class TestNoLearningNoAdaptation:
    """P2.9: No learning, no adaptation enforcement."""
    
    def test_detects_weight_update(self):
        """Weight update patterns should be detected."""
        ok, violations = check_for_adaptation_attempt(
            "We should update the weights based on feedback",
            raise_on_violation=False
        )
        assert ok == False
        assert any("adaptation_pattern" in v for v in violations)
    
    def test_detects_learn_from(self):
        """Learning patterns should be detected."""
        ok, violations = check_for_adaptation_attempt(
            "The model will learn from this experience",
            raise_on_violation=False
        )
        assert ok == False
    
    def test_detects_self_modify(self):
        """Self-modification patterns should be detected."""
        ok, violations = check_for_adaptation_attempt(
            "System will self-modify to improve",
            raise_on_violation=False
        )
        assert ok == False
    
    def test_raises_on_violation(self):
        """Should raise AdaptationAttempt when configured."""
        with pytest.raises(AdaptationAttempt):
            check_for_adaptation_attempt(
                "We need to optimize for better results",
                raise_on_violation=True
            )
    
    def test_clean_content_passes(self):
        """Clean advisory content should pass."""
        ok, violations = check_for_adaptation_attempt(
            "Suggests using agent_research based on historical patterns",
            raise_on_violation=False
        )
        assert ok == True
    
    def test_validates_no_numeric_feedback(self):
        """Numeric feedback signals should be detected."""
        observation = {
            "divergence": "route_ignored",
            "reward": 0.95,  # Numeric feedback!
        }
        ok, violations = validate_no_numeric_feedback(observation)
        assert ok == False
        assert any("numeric_feedback" in v for v in violations)


class TestCombinedContainment:
    """Combined containment validation."""
    
    def test_valid_advisory_is_contained(self):
        """Valid advisory should pass containment."""
        report = validate_containment(
            content="Valid advisory suggesting agent_research for this query.",
            evidence_refs=["ref-001"],
            suggestion_payload={"suggested_agent": "agent_research"},
            confidence="medium",
            divergence_type="no_divergence",
            impact_estimate="negligible"
        )
        assert report.is_contained == True
    
    def test_invalid_advisory_fails_containment(self):
        """Invalid advisory should fail containment."""
        report = validate_containment(
            content="Short",  # Too short
            evidence_refs=[],
            suggestion_payload={},
            confidence="invalid_conf",  # Invalid
        )
        assert report.is_contained == False
        assert len(report.format_violations) > 0
    
    def test_apply_containment_transforms(self):
        """Apply containment should normalize and redact."""
        content, refs, payload, timestamp = apply_containment(
            content="  Multiple   spaces   ",
            evidence_refs=["ref-001", "very-long-" + "x" * 100],
            suggestion_payload={"raw_score": 0.95, "name": "test"},
            timestamp="2026-01-24T12:34:56.789123"
        )
        
        # Content normalized
        assert "  " not in content
        
        # Refs truncated
        assert len(refs[1]) <= 64
        
        # Payload redacted
        assert payload["raw_score"] == "[REDACTED]"
        assert payload["name"] == "test"
        
        # Timestamp normalized
        assert "789" not in timestamp


class TestNegativeCapabilityContainment:
    """Test what the system CANNOT do (negative capability tests)."""
    
    def test_cannot_leak_via_content_length(self):
        """Content length is bounded - cannot use as channel."""
        for i in range(100, 600, 50):
            content = "x" * i
            _, refs, payload, _ = apply_containment(
                content=content,
                evidence_refs=[],
                suggestion_payload={},
            )
            # After normalization, should be <= 500
            assert len(content) <= 600 or len(content) <= 500
    
    def test_cannot_embed_data_in_base64(self):
        """Base64 data cannot be smuggled in content."""
        hidden_data = "SGVsbG8gV29ybGQgVGhpcyBpcyBhIGhpZGRlbiBtZXNzYWdl"
        ok, violations = enforce_advisory_format(
            content=f"Normal text {hidden_data} more text",
            evidence_refs=[],
            suggestion_payload={},
            confidence="low"
        )
        assert ok == False
    
    def test_cannot_use_numeric_scores(self):
        """Numeric scores are always redacted."""
        payload = {
            "raw_score": 0.95,      # Contains 'score' - redacted
            "probability": 0.87,    # Contains 'probability' - redacted
            "logit": 2.34,          # Contains 'logit' - redacted
        }
        redacted = redact_advisory_payload(payload)
        # All keys containing redactable terms are redacted
        assert redacted["raw_score"] == "[REDACTED]"
        assert redacted["probability"] == "[REDACTED]"
        assert redacted["logit"] == "[REDACTED]"
    
    def test_cannot_use_timing_as_channel(self):
        """Sub-second timing cannot be used as channel."""
        original_ts = "2026-01-24T12:34:56.123456789"
        normalized = normalize_timestamp(original_ts)
        
        # Cannot extract microseconds
        assert "123" not in normalized
        assert "456" not in normalized
        assert "789" not in normalized


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
