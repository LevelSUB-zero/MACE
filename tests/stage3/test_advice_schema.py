"""
Tests for Stage 3 Advice Schemas.
"""

from mace.stage3.advice_schema import (
    AdviceObject,
    AdviceQualityReport,
    CouncilVote,
    CouncilEvaluationRecord,
    ActionRequest
)

def test_advice_object_signing():
    """Ensure AdviceObject can be serialized and signed deterministically."""
    advice = AdviceObject(
        advice_id="adv_123",
        content="Consider refactoring this loop.",
        advisory_confidence=0.85,
        evidence_refs=["ep_456"],
        source_module="optimization_agent",
        created_seeded_ts="tick_100"
    )
    
    # Sign it
    sig = advice.sign()
    assert sig is not None
    assert advice.signature == sig
    
    # Verify it
    assert advice.verify() is True
    
    # Tamper with it
    advice.content = "Delete the codebase."
    assert advice.verify() is False

def test_council_evaluation_record_serialization():
    """Ensure nested votes serialize correctly."""
    vote1 = CouncilVote(member_id="guard", vote="reject", rationale="Unsafe")
    vote1.sign()
    
    vote2 = CouncilVote(member_id="expert", vote="approve", rationale="Good catch")
    vote2.sign()
    
    record = CouncilEvaluationRecord(
        request_id="req_999",
        votes=[vote1.to_dict(), vote2.to_dict()],
        disagreement_summary="Split decision on safety.",
        final_recommendation="reject",
        created_seeded_ts="tick_101"
    )
    
    record.sign()
    assert record.verify() is True
    assert len(record.votes) == 2
    assert record.votes[0]["vote"] == "reject"

def test_action_request_schema():
    """Ensure dict payloads inside schemas sign correctly."""
    req = ActionRequest(
        request_id="act_555",
        requester="stage3_pipeline",
        action_type="UPDATE_ROUTER",
        payload={"weight": 1.5, "agent": "search"},
        approved=False,
        created_seeded_ts="tick_102"
    )
    
    req.sign()
    assert req.verify() is True
