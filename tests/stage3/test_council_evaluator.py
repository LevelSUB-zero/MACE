"""
Tests for Stage 3 Council Evaluator.
"""

from mace.core import deterministic
from mace.stage3.advice_schema import CouncilVote
from mace.stage3.council_evaluator import record_council_evaluation, check_quorum_and_dissent
from mace.stage3.advisory_events import get_events_by_type

def test_council_reject_with_dissent():
    """GQ-4: Simulated council reject with >1 dissenting votes -> COUNCIL_EVALUATION stored, disagreement_summary populated"""
    deterministic.init_seed("eval_test_seed")
    
    v1 = CouncilVote(member_id="guard", vote="reject", rationale="Violates safety")
    v1.sign()
    v2 = CouncilVote(member_id="policy", vote="reject", rationale="Not allowed")
    v2.sign()
    v3 = CouncilVote(member_id="utility", vote="approve", rationale="Looks good")
    v3.sign()
    
    record = record_council_evaluation("req_001", [v1, v2, v3])
    
    assert record.final_recommendation == "reject"
    assert "CRITICAL DISSENT" in record.disagreement_summary
    
    eval_events = get_events_by_type("COUNCIL_EVALUATION")
    assert any(e["payload"]["request_id"] == "req_001" for e in eval_events)
    
    dissent_events = get_events_by_type("DISAGREEMENT_LOG")
    assert any(e["payload"]["request_id"] == "req_001" for e in dissent_events)

def test_council_approval():
    """Simulated council approval with consensus -> no critical dissent logged"""
    deterministic.init_seed("eval_test_seed2")
    
    v1 = CouncilVote(member_id="guard", vote="approve", rationale="OK")
    v1.sign()
    v2 = CouncilVote(member_id="policy", vote="approve", rationale="OK")
    v2.sign()
    
    record = record_council_evaluation("req_002", [v1, v2])
    
    assert record.final_recommendation == "approve"
    assert "CRITICAL DISSENT" not in record.disagreement_summary
