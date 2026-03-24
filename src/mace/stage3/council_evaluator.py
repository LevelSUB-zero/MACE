"""
Module: council_evaluator
Stage: 3
Purpose: Records council votes, detects dissent and quorum requirements,
         and logs evaluations and disagreements to the advisory event stream.

Part of MACE (Meta Aware Cognitive Engine).
Spec: docs/phase3/advisory_system_spec.md § 3.3.6
"""

from typing import List, Dict, Any
from mace.core import deterministic
from mace.stage3.advice_schema import CouncilVote, CouncilEvaluationRecord
from mace.stage3 import advisory_events

def check_quorum_and_dissent(votes: List[CouncilVote]) -> str:
    """
    Check quorum and format a disagreement summary string if >1 member rejects.
    Returns:
        Disagreement summary string (empty if consensus or acceptable dissent).
    """
    rejects = [v for v in votes if v.vote == "reject"]
    if len(rejects) > 1:
        reasons = "; ".join([f"{r.member_id}: {r.rationale}" for r in rejects])
        return f"CRITICAL DISSENT ({len(rejects)} rejects): {reasons}"
    elif len(rejects) == 1:
        return f"Minor dissent: {rejects[0].member_id} rejected."
    return ""

def record_council_evaluation(request_id: str, votes: List[CouncilVote]) -> CouncilEvaluationRecord:
    """
    Record council votes, evaluate consensus, and emit events.
    """
    disagreement_summary = check_quorum_and_dissent(votes)
    
    # Calculate final recommendation (simple majority)
    approve_count = sum(1 for v in votes if v.vote == "approve")
    reject_count = sum(1 for v in votes if v.vote == "reject")
    
    if reject_count > len(votes) / 2:
        final_rec = "reject"
    elif approve_count > len(votes) / 2:
        final_rec = "approve"
    else:
        final_rec = "abstain"
        
    seed = deterministic.get_seed() or "evaluator_fallback"
    if deterministic.get_seed() is None:
        deterministic.init_seed(seed)
        
    eval_ts = deterministic.deterministic_id("eval_tick", request_id)
    
    record = CouncilEvaluationRecord(
        request_id=request_id,
        votes=[v.to_dict() for v in votes],
        disagreement_summary=disagreement_summary,
        final_recommendation=final_rec,
        created_seeded_ts=eval_ts
    )
    record.sign()
    
    # Log the general evaluation event
    advisory_events.append_advisory_event(
        "COUNCIL_EVALUATION",
        "council_evaluator",
        record.to_dict(),
        [request_id]
    )
    
    # If there is critical dissent, explicitly log it
    if "CRITICAL DISSENT" in disagreement_summary:
        advisory_events.append_advisory_event(
            "DISAGREEMENT_LOG",
            "council_evaluator",
            {
                "request_id": request_id, 
                "summary": disagreement_summary,
                "reject_count": reject_count
            },
            [request_id]
        )
        
    return record
