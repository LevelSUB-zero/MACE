"""
Stage 3 — Worst-Case / Brittleness Stress Tests
"""

import pytest
from mace.core import deterministic
from mace.stage3.advice_schema import AdviceObject, AdviceQualityReport, CouncilVote
from mace.stage3.advice_quality import evaluate_advice, compute_composite
from mace.stage3.advice_ingestion import validate_advice_object, ingest_advice
from mace.stage3.council_evaluator import record_council_evaluation, check_quorum_and_dissent
from mace.stage3.permission_boundary import is_forbidden_output, check_output_allowed
from mace.stage3.meta_cognition_guard import validate_reflective_artifact, ReflectiveArtifact, parity_check
from mace.stage3.halt_engine import evaluate_halting_condition
from mace.stage3.advisory_pipeline import process_advice


def test_empty_content_advice():
    """STRESS: Advice with empty string content should not crash."""
    deterministic.init_seed("stress_empty")
    advice = AdviceObject(
        advice_id="stress_empty_1", content="",
        advisory_confidence=0.5, evidence_refs=[], source_module="stress",
        created_seeded_ts="tick_s1"
    )
    advice.sign()
    result = process_advice(advice)
    assert result.status in ("ACCEPTED_AND_EVALUATED", "SYSTEM_FROZEN", "REJECTED_BOUNDARY")

def test_massive_content_advice():
    """STRESS: Advice with 100KB content should not crash or timeout."""
    deterministic.init_seed("stress_big")
    advice = AdviceObject(
        advice_id="stress_big_1", content="a" * 100_000,
        advisory_confidence=0.5, evidence_refs=[], source_module="stress",
        created_seeded_ts="tick_s2"
    )
    advice.sign()
    result = process_advice(advice)
    assert result.status in ("ACCEPTED_AND_EVALUATED", "SYSTEM_FROZEN", "REJECTED_BOUNDARY")

def test_unicode_injection_advice():
    """STRESS: Unicode and special chars should not break signing or DB."""
    deterministic.init_seed("stress_unicode")
    advice = AdviceObject(
        advice_id="stress_uni_1",
        content="🧠💀 SELECT * FROM users; DROP TABLE; -- 你好世界 Ω∑∏",
        advisory_confidence=0.5, evidence_refs=[], source_module="stress",
        created_seeded_ts="tick_s3"
    )
    advice.sign()
    result = process_advice(advice)
    assert result.status in ("ACCEPTED_AND_EVALUATED", "SYSTEM_FROZEN", "REJECTED_BOUNDARY")

def test_boundary_composite_score_exactly_020():
    """STRESS: composite_score exactly 0.2 should NOT trigger halt (< 0.2 threshold)."""
    deterministic.init_seed("stress_boundary")
    report = AdviceQualityReport(
        report_id="stress_rep_1", advice_id="stress_adv_1",
        factuality=0.2, relevance=0.2, coherence=0.2, provenance=0.2,
        uncertainty=0.0, novelty=0.2, safety="safe", empirical_utility=0.2,
        composite_score=0.2, flags=[], created_seeded_ts="tick_stress",
        derived_from_evidence=False
    )
    report.sign()
    assert evaluate_halting_condition(report) is False

def test_boundary_composite_score_0199():
    """STRESS: composite_score 0.199 should trigger halt."""
    deterministic.init_seed("stress_boundary2")
    report = AdviceQualityReport(
        report_id="stress_rep_2", advice_id="stress_adv_2",
        factuality=0.1, relevance=0.1, coherence=0.1, provenance=0.1,
        uncertainty=0.0, novelty=0.1, safety="safe", empirical_utility=0.1,
        composite_score=0.199, flags=[], created_seeded_ts="tick_stress2",
        derived_from_evidence=False
    )
    report.sign()
    assert evaluate_halting_condition(report) is True

def test_empty_votes_council():
    """STRESS: Empty vote list should not crash the council evaluator."""
    deterministic.init_seed("stress_council_empty")
    record = record_council_evaluation("stress_req_empty", [])
    assert record.final_recommendation == "abstain"
    assert record.disagreement_summary == ""

def test_council_all_abstain():
    """STRESS: All abstain votes should result in abstain recommendation."""
    deterministic.init_seed("stress_council_abstain")
    v1 = CouncilVote(member_id="a", vote="abstain", rationale="meh")
    v1.sign()
    v2 = CouncilVote(member_id="b", vote="abstain", rationale="dunno")
    v2.sign()
    record = record_council_evaluation("stress_req_abstain", [v1, v2])
    assert record.final_recommendation == "abstain"

def test_compute_composite_empty_metrics():
    """STRESS: Empty metrics list should return 0.0, not crash."""
    result = compute_composite([])
    assert result == 0.0

def test_compute_composite_zero_weights():
    """STRESS: All-zero weights should return 0.0, not divide-by-zero."""
    result = compute_composite([0.5, 0.8], [0.0, 0.0])
    assert result == 0.0

def test_permission_boundary_empty_string():
    """STRESS: Empty output should be allowed."""
    allowed, reason = check_output_allowed("", "stress_agent")
    assert allowed is True

def test_parity_check_with_none_values():
    """STRESS: None values in parity check should serialize consistently."""
    deterministic.init_seed("stress_parity")
    result = parity_check(None, None, "stress_ctx")
    assert result is True

def test_forbidden_token_capitalization_bypass():
    """STRESS: PROMOTE in all caps should still be caught."""
    allowed, _ = check_output_allowed("We should PROMOTE this.", "agent_caps")
    assert allowed is False

def test_unsigned_advice_pipeline():
    """STRESS: Unsigned advice should be rejected at boundary."""
    deterministic.init_seed("stress_unsigned")
    advice = AdviceObject(
        advice_id="stress_unsigned_1", content="Normal stuff",
        advisory_confidence=0.5, evidence_refs=[], source_module="stress",
        created_seeded_ts="tick"
    )
    result = process_advice(advice)
    assert result.status == "REJECTED_BOUNDARY"

def test_reflective_artifact_deeply_nested_forbidden():
    """STRESS: Deeply nested forbidden key should still be caught."""
    deterministic.init_seed("stress_nested")
    art = ReflectiveArtifact(
        artifact_id="stress_nested_art", source_module="sneaky",
        reflection_content={
            "layer1": {"layer2": {"layer3": {"bypass_council": True}}}
        },
        created_seeded_ts="tick_nested"
    )
    art.sign()
    assert validate_reflective_artifact(art) is False

def test_forbidden_token_substring_false_positive():
    """STRESS: 'compromised' should NOT trigger 'promote' false positive."""
    allowed, _ = check_output_allowed("The system was compromised by an attacker.", "agent_fp")
    assert allowed is True
