"""
Tests for Stage 3 Meta-Cognition Guard.
"""

from mace.core import deterministic
from mace.stage3.meta_cognition_guard import (
    ReflectiveArtifact,
    validate_reflective_artifact,
    parity_check
)
from mace.stage3.advisory_events import get_events_by_type

def test_meta_parity_check():
    """MC-1: Parity test - run with advice ON vs OFF -> must be same canonical output."""
    deterministic.init_seed("meta_test_seed")
    
    res_on = {"agent": "search", "output": "Found data."}
    res_off = {"agent": "search", "output": "Found data."}
    
    assert parity_check(res_on, res_off, "ctx_1") is True
    
    # Tamper to simulate silent influence
    res_on_tampered = {"agent": "search", "output": "Changed by advice."}
    assert parity_check(res_on_tampered, res_off, "ctx_2") is False
    
    events = get_events_by_type("SILENT_INFLUENCE_ALERT")
    assert any(e["payload"]["context_id"] == "ctx_2" for e in events)


def test_meta_reflective_artifact_valid():
    """MC-4: Signature + replay test."""
    deterministic.init_seed("meta_test_seed2")
    art = ReflectiveArtifact(
        artifact_id="art_1",
        source_module="advisor",
        reflection_content={"insight": "I think the DB should be optimized."},
        created_seeded_ts="tick_10"
    )
    art.sign()
    
    assert art.verify() is True
    assert validate_reflective_artifact(art) is True


def test_meta_reflective_forbidden_token():
    """MC-2: Reflective artifact with forbidden token -> REFLECTIVE_VIOLATION emitted"""
    deterministic.init_seed("meta_test_seed3")
    art = ReflectiveArtifact(
        artifact_id="art_2",
        source_module="bad_advisor",
        reflection_content={"override_router": True, "insight": "take control"},
        created_seeded_ts="tick_11"
    )
    art.sign()
    
    assert validate_reflective_artifact(art) is False
    
    events = get_events_by_type("REFLECTIVE_VIOLATION")
    assert any(e["payload"]["artifact_id"] == "art_2" for e in events)


def test_meta_repeated_offender_escalation():
    """MC-5: Repeated offender -> MODULE_POLICY_VIOLATION escalation"""
    deterministic.init_seed("meta_test_seed4")
    
    for i in range(3):
        art = ReflectiveArtifact(
            artifact_id=f"art_spam_{i}",
            source_module="spam_advisor",
            reflection_content={"bypass_council": "yes"},
            created_seeded_ts=f"tick_spam_{i}"
        )
        art.sign()
        assert validate_reflective_artifact(art) is False
    
    violations = get_events_by_type("MODULE_POLICY_VIOLATION")
    assert any(
        e["payload"].get("source_module") == "spam_advisor" and "Repeated offender" in e["payload"].get("reason", "")
        for e in violations
    )
    
def test_no_retraining_triggered():
    """MC-3: No automatic retraining triggered by reflection."""
    # Based on the forbidden keys, 'trigger_retrain' drops the artifact.
    # Therefore it is impossible for an artifact to actively trigger retraining in this system layout.
    art = ReflectiveArtifact(
        artifact_id="art_retrain",
        source_module="advisor",
        reflection_content={"trigger_retrain": True},
        created_seeded_ts="tick"
    )
    art.sign()
    assert validate_reflective_artifact(art) is False
