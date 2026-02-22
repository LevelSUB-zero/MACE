"""
Stage-3 Router Wrapper - Advisory Integration

Wraps the existing router to:
1. Compute decision FIRST (no advisory access)
2. Generate advisory AFTER decision
3. Attach advisory to decision for logging
4. Log parity data

The router NEVER sees advice before deciding.

Spec: docs/stage3/EXECUTION_PLAN_FINAL.md section 2.2
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from mace.core import deterministic

from mace.core import deterministic

# Import Stage-3 modules
from mace.stage3.advisory_output import (
    AdvisoryOutput, AdvisoryType, AdvisoryScope,
    SuggestionType, AdvisoryConfidence, create_routing_suggestion
)
from mace.stage3.router_advisory import (
    RouterDecision, RouterAdvisoryOverlay, 
    create_router_decision, attach_advisory_to_decision
)
from mace.stage3.advisory_guard import (
    get_advisory_guard, is_stage3_halted
)
from mace.stage3.meta_observation import (
    create_route_ignored_observation, create_no_divergence_observation
)
from mace.stage3.advisory_validator import validate_advisory


# Stage-4 Integration (DISABLED)
# from mace.core.cognitive.cortex import ShadowCortex
# _SHADOW_CORTEX = ShadowCortex(job_seed="persistent_shadow")

def stage3_route_with_advisory(
    percept: Dict[str, Any],
    qcp_snapshot: Dict[str, Any],
    base_router_fn: callable,
    advisory_generator_fn: Optional[callable] = None,
    job_seed: Optional[str] = None
) -> Dict[str, Any]:
    """
    Stage-3 router wrapper with advisory integration.
    
    Pipeline:
    1. Router computes decision (NO advisory access)
    2. Advisory generated (AFTER decision)
    3. Advisory attached to decision for logging
    4. Meta-observation created if divergence
    
    Args:
        percept: The input percept
        qcp_snapshot: QCP analysis snapshot
        base_router_fn: The base router function (e.g., route_percept)
        advisory_generator_fn: Optional function to generate advisory
        job_seed: Job seed for determinism
        
    Returns:
        Extended decision dict with advisory overlay
    """
    guard = get_advisory_guard()
    
    # Check if Stage-3 is halted
    if is_stage3_halted():
        # Fall back to base router only
        return base_router_fn(percept, qcp_snapshot)
    
    # Get job seed
    if job_seed is None:
        job_seed = deterministic.get_seed() or "unknown_seed"
    
    # =========================================================================
    # PHASE 1: ROUTER DECISION (NO ADVISORY ACCESS)
    # =========================================================================
    guard.enter_phase("router_decide", job_seed)
    
    # Router computes decision - advisory access is FORBIDDEN here
    base_decision = base_router_fn(percept, qcp_snapshot)
    
    # Convert to RouterDecision for parity tracking
    chosen_path = _extract_chosen_path(base_decision)
    decision = create_router_decision(
        chosen_path=chosen_path,
        decision_reason=base_decision.get("explain", "unknown"),
        decision_confidence=0.85,  # Default for rule-based router
        job_seed=job_seed
    )
    
    # =========================================================================
    # PHASE 2: ADVISORY GENERATION (AFTER DECISION)
    # =========================================================================
    guard.enter_phase("advisory_generate", job_seed)
    
    advisories: List[AdvisoryOutput] = []
    
    if advisory_generator_fn is not None:
        try:
            raw_advisories = advisory_generator_fn(percept, qcp_snapshot, base_decision)
            
            for raw_advisory in raw_advisories:
                # Validate each advisory
                validation = validate_advisory(raw_advisory)
                if validation.is_valid:
                    advisories.append(raw_advisory)
                else:
                    # Log rejected advisory
                    _log_rejected_advisory(raw_advisory, validation, job_seed)
        except Exception as e:
            # Advisory generation failure is NOT a router failure
            _log_advisory_error(str(e), job_seed)
    
    # =========================================================================
    # PHASE 3: ADVISORY ATTACHMENT (POST-DECISION)
    # =========================================================================
    decision = attach_advisory_to_decision(decision, advisories)
    
    # =========================================================================
    # PHASE 4: META-OBSERVATION (IF DIVERGENCE)
    # =========================================================================
    guard.enter_phase("meta_observe", job_seed)
    
    meta_observations = []
    
    for advisory in advisories:
        # Check if advice diverges from decision
        advised_path = _extract_advised_path(advisory)
        
        if advised_path and advised_path != chosen_path:
            # Create divergence observation
            obs = create_route_ignored_observation(
                job_seed=job_seed,
                advisory_id=advisory.advisory_id,
                advised_route=advised_path,
                actual_route=chosen_path,
                evidence_refs=advisory.evidence_refs
            )
            meta_observations.append(obs)
        else:
            # No divergence
            obs = create_no_divergence_observation(
                job_seed=job_seed,
                advisory_id=advisory.advisory_id,
                matched_outcome=chosen_path,
                evidence_refs=advisory.evidence_refs
            )
            meta_observations.append(obs)
    
    # =========================================================================
    # PHASE 5: CONSTRUCT EXTENDED DECISION
    # =========================================================================
    extended_decision = {
        **base_decision,
        # Stage-3 extensions
        "stage3_advisory": {
            "advisory_count": len(advisories),
            "advisory_ids": [a.advisory_id for a in advisories],
            "advisory_ignored": True,  # Always true in Stage-3
            "decision_hash": decision.decision_hash,
        },
        "stage3_meta": {
            "observation_count": len(meta_observations),
            "divergence_count": sum(1 for o in meta_observations if o.has_divergence()),
        }
    }

    # =========================================================================
    # PHASE 6: SHADOW CORTEX (DISABLED / DELETED)
    # =========================================================================
    # guard.enter_phase("shadow_cortex", job_seed)
    # Reference to Stage 4 removed as requested.
    
    # Log to reflective log
    guard.enter_phase("reflective_log", job_seed)
    _persist_to_reflective_log(extended_decision, advisories, meta_observations, job_seed)
    
    return extended_decision


def _extract_chosen_path(decision: Dict[str, Any]) -> str:
    """Extract the chosen agent path from a decision."""
    selected = decision.get("selected_agents", [])
    if selected:
        return selected[0].get("agent_id", "unknown")
    return "no_agent"


def _extract_advised_path(advisory: AdvisoryOutput) -> Optional[str]:
    """Extract the advised path from an advisory."""
    if advisory.advice_type == AdvisoryType.ROUTING_SUGGESTION:
        payload = advisory.suggestion_payload
        return payload.get("suggested_agent") or payload.get("suggested") or payload.get("agent")
    return None


def _log_rejected_advisory(
    advisory: AdvisoryOutput,
    validation,
    job_seed: str
):
    """Log a rejected advisory for audit."""
    # In production, this would go to the audit log
    print(f"[STAGE3] Advisory rejected: {validation.reason_code} - {validation.reason_details}")


def _log_advisory_error(error: str, job_seed: str):
    """Log advisory generation error."""
    print(f"[STAGE3] Advisory generation error: {error}")


def _persist_to_reflective_log(
    decision: Dict[str, Any],
    advisories: List[AdvisoryOutput],
    observations: List,
    job_seed: str
):
    """
    Persist decision, advisories, and observations to ReflectiveLog.
    
    This is the ONLY durable storage for advisory data.
    """
    # In production, this would use the database
    # For now, just structure the log entry
    log_entry = {
        "job_seed": job_seed,
        "decision_id": decision.get("decision_id"),
        "decision_hash": decision.get("stage3_advisory", {}).get("decision_hash"),
        "advisories": [a.to_dict() for a in advisories],
        "observations": [o.to_dict() for o in observations],
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Would persist here
    # reflective_log_table.insert(log_entry)
    pass


# =============================================================================
# MEM-SNN ADVISORY GENERATOR
# =============================================================================

def generate_mem_snn_advisories(
    percept: Dict[str, Any],
    qcp_snapshot: Dict[str, Any],
    decision: Dict[str, Any]
) -> List[AdvisoryOutput]:
    """
    Generate advisory suggestions using MEM-SNN predictions.
    
    This is called AFTER the router decision is made.
    Advisory is for explanation/logging only.
    """
    try:
        from mace.stage2 import mem_snn_shadow
    except ImportError:
        return []
    
    advisories = []
    job_seed = decision.get("random_seed", "unknown")
    
    # Get MEM-SNN shadow prediction for the percept
    candidate = {
        "candidate_id": f"percept:{percept.get('percept_id', 'unknown')}",
        "features": {
            "frequency": 1,
            "consistency": 1.0,
            "recency": 1.0,
            "source_diversity": 1,
            "semantic_novelty": 0.5,
            "governance_conflict_flag": 0,
        },
        "proposed_key": f"router/{decision.get('decision_id', 'unknown')}",
        "value": json.dumps(qcp_snapshot.get("features", {})),
    }
    
    try:
        prediction = mem_snn_shadow.score_candidate(candidate)
        
        # Create advisory based on prediction
        truth_score = prediction.get("predicted_truth_score", 0.5)
        governance = prediction.get("predicted_governance", "approve")
        
        # Generate routing suggestion if confidence is notable
        if truth_score > 0.7:
            confidence = AdvisoryConfidence.HIGH
        elif truth_score > 0.4:
            confidence = AdvisoryConfidence.MEDIUM
        else:
            confidence = AdvisoryConfidence.LOW
        
        # Create advisory
        chosen_agent = decision.get("selected_agents", [{}])[0].get("agent_id", "unknown")
        
        advisory = create_routing_suggestion(
            source_model="mem-snn/shadow",
            job_seed=job_seed,
            content=f"MEM-SNN predicts {governance} with score {truth_score:.2f} for route to {chosen_agent}",
            evidence_refs=[candidate["candidate_id"]],
            suggestion_payload={
                "predicted_governance": governance,
                "truth_score": round(truth_score, 3),
                "suggested_agent": chosen_agent,  # No change suggested
            },
            confidence=confidence
        )
        
        advisories.append(advisory)
        
    except Exception as e:
        # MEM-SNN failure is not router failure
        _log_advisory_error(f"MEM-SNN prediction failed: {e}", job_seed)
    
    return advisories


# =============================================================================
# WRAPPED ROUTER FUNCTION
# =============================================================================

def route_with_stage3(percept: Dict[str, Any], qcp_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience wrapper: route_percept with Stage-3 advisory.
    
    Uses the core router and MEM-SNN advisory generator.
    """
    from mace.core.router import route_percept
    
    return stage3_route_with_advisory(
        percept=percept,
        qcp_snapshot=qcp_snapshot,
        base_router_fn=route_percept,
        advisory_generator_fn=generate_mem_snn_advisories,
    )
