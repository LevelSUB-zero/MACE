"""
Router Advisory Overlay - Stage-3 Non-Causal Advisory Attachment

The router pipeline is explicitly split:
1. Deterministic decision
2. Decision finalization
3. Advisory overlay attachment
4. Reflective logging

The router NEVER:
- Sees advice before deciding
- Re-evaluates after advice
- Retries due to advice

Router output must be identical with advisory enabled or disabled.
Advice can disagree. Disagreement is logged, not resolved.

Spec: docs/stage3/EXECUTION_PLAN_FINAL.md section 2.2
Spec: docs/stage3/advisory_system_spec.md section 3.2
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from .advisory_output import AdvisoryOutput


class DivergenceClass(str, Enum):
    """Classification of divergence between advice and decision."""
    EXPLAIN_ONLY = "explain_only"           # Acceptable: advice for explanation only
    UNAUTHORIZED_USAGE = "unauthorized_usage"  # VIOLATION: advice influenced decision
    UNKNOWN = "unknown"                     # Requires manual review


@dataclass
class RouterDecision:
    """
    Extended router decision with advisory overlay.
    
    The router computes decision FIRST, then advisory is attached for logging.
    Advisory NEVER influences the decision.
    """
    # Core decision (computed WITHOUT advice)
    chosen_path: str
    decision_reason: str
    decision_confidence: float
    
    # Advisory overlay (attached AFTER decision)
    advisory_suggestions: List[AdvisoryOutput] = field(default_factory=list)
    advisory_ignored: bool = True  # Always true in proper Stage-3
    
    # Parity tracking
    job_seed: str = ""
    decision_hash: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def __post_init__(self):
        if not self.decision_hash:
            self.decision_hash = self._compute_decision_hash()
    
    def _compute_decision_hash(self) -> str:
        """Compute hash of core decision (excludes advisory)."""
        core = json.dumps({
            "chosen_path": self.chosen_path,
            "decision_reason": self.decision_reason,
            "decision_confidence": self.decision_confidence,
        }, sort_keys=True)
        return hashlib.sha256(core.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chosen_path": self.chosen_path,
            "decision_reason": self.decision_reason,
            "decision_confidence": self.decision_confidence,
            "advisory_suggestions": [a.to_dict() for a in self.advisory_suggestions],
            "advisory_ignored": self.advisory_ignored,
            "job_seed": self.job_seed,
            "decision_hash": self.decision_hash,
            "created_at": self.created_at,
        }


@dataclass
class RouterDivergenceEvent:
    """
    Event logged when advice diverges from actual decision.
    
    Per spec: docs/stage3/advisory_system_spec.md section 3.4
    """
    event_type: str = "ROUTER_DIVERGENCE"
    event_id: str = ""
    job_seed: str = ""
    iteration_index: int = 0
    
    # Decision comparison
    decision_no_advice_hash: str = ""
    decision_with_advice_hash: str = ""
    
    # Advisory reference
    advice_refs: List[str] = field(default_factory=list)
    advice_handling: Dict[str, Any] = field(default_factory=dict)
    
    # Divergence details
    diff_summary: str = ""
    divergence_class: DivergenceClass = DivergenceClass.UNKNOWN
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    detector_signature: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "job_seed": self.job_seed,
            "iteration_index": self.iteration_index,
            "decision_no_advice_hash": self.decision_no_advice_hash,
            "decision_with_advice_hash": self.decision_with_advice_hash,
            "advice_refs": self.advice_refs,
            "advice_handling": self.advice_handling,
            "diff_summary": self.diff_summary,
            "divergence_class": self.divergence_class.value,
            "created_at": self.created_at,
            "detector_signature": self.detector_signature,
        }


class RouterAdvisoryOverlay:
    """
    Manages advisory overlay attachment to router decisions.
    
    Key invariant: Router output must be identical with advisory enabled or disabled.
    """
    
    def __init__(self):
        self._iteration_traces: List[Dict[str, Any]] = []
        self._divergence_events: List[RouterDivergenceEvent] = []
    
    def attach_advisory(
        self,
        decision: RouterDecision,
        advisory_suggestions: List[AdvisoryOutput]
    ) -> RouterDecision:
        """
        Attach advisory suggestions to a router decision.
        
        This happens AFTER the decision is made.
        Advisory suggestions are for logging only.
        """
        decision.advisory_suggestions = advisory_suggestions
        decision.advisory_ignored = True  # Always true
        return decision
    
    def compute_parity_check(
        self,
        job_seed: str,
        decision_no_advice: RouterDecision,
        decision_with_advice: Optional[RouterDecision] = None
    ) -> Optional[RouterDivergenceEvent]:
        """
        Check parity between decisions with and without advice.
        
        If decision_with_advice differs from decision_no_advice,
        log a divergence event.
        
        Returns divergence event if divergence detected, None otherwise.
        """
        if decision_with_advice is None:
            return None
        
        # Compare core decision hashes
        hash_no_advice = decision_no_advice.decision_hash
        hash_with_advice = decision_with_advice.decision_hash
        
        if hash_no_advice == hash_with_advice:
            return None  # No divergence
        
        # Generate divergence event
        event_id = hashlib.sha256(
            f"{job_seed}:div:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Compute deterministic diff summary
        diff_parts = []
        if decision_no_advice.chosen_path != decision_with_advice.chosen_path:
            diff_parts.append(f"changed_path:[{decision_no_advice.chosen_path}->{decision_with_advice.chosen_path}]")
        if decision_no_advice.decision_confidence != decision_with_advice.decision_confidence:
            diff_parts.append(f"changed_confidence:[{decision_no_advice.decision_confidence}->{decision_with_advice.decision_confidence}]")
        
        diff_summary = "; ".join(diff_parts) if diff_parts else "unknown_diff"
        
        # Classify divergence
        # If advisory was supposed to be ignored but decision changed, it's unauthorized
        divergence_class = DivergenceClass.UNAUTHORIZED_USAGE  # Default to most severe
        
        event = RouterDivergenceEvent(
            event_id=event_id,
            job_seed=job_seed,
            decision_no_advice_hash=hash_no_advice,
            decision_with_advice_hash=hash_with_advice,
            advice_refs=[a.advisory_id for a in decision_with_advice.advisory_suggestions],
            advice_handling={"advice_considered": False, "advice_handling": "ignored"},
            diff_summary=diff_summary,
            divergence_class=divergence_class,
            detector_signature=hashlib.sha256(diff_summary.encode()).hexdigest()[:16],
        )
        
        self._divergence_events.append(event)
        return event
    
    def create_iteration_trace(
        self,
        job_seed: str,
        decision_no_advice: RouterDecision,
        decision_with_advice: Optional[RouterDecision],
        advice_refs: List[str],
        explain_with_advice: bool = False
    ) -> Dict[str, Any]:
        """
        Create iteration trace with both decisions.
        
        Per spec: "Every router run logs both the 'no-advice' and 'with-advice' 
        decision traces and a small, deterministic divergence record."
        """
        advice_handling = {
            "advice_considered": explain_with_advice,
            "advice_handling": "logged_for_explanation" if explain_with_advice else "ignored",
            "ignoring_reason_code": None if explain_with_advice else "NOT_REQUESTED",
        }
        
        trace = {
            "job_seed": job_seed,
            "decision_no_advice": decision_no_advice.to_dict(),
            "decision_with_advice": decision_with_advice.to_dict() if decision_with_advice else None,
            "advice_refs": advice_refs,
            "advice_handling": advice_handling,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self._iteration_traces.append(trace)
        return trace
    
    def get_divergence_events(self) -> List[RouterDivergenceEvent]:
        """Get all divergence events."""
        return self._divergence_events.copy()
    
    def has_unauthorized_divergence(self) -> bool:
        """Check if any unauthorized divergence was detected."""
        return any(
            e.divergence_class == DivergenceClass.UNAUTHORIZED_USAGE

            for e in self._divergence_events
        )


# Convenience functions
def create_router_decision(
    chosen_path: str,
    decision_reason: str,
    decision_confidence: float,
    job_seed: str
) -> RouterDecision:
    """Create a router decision (without advisory)."""
    return RouterDecision(
        chosen_path=chosen_path,
        decision_reason=decision_reason,
        decision_confidence=decision_confidence,
        job_seed=job_seed,
    )


def attach_advisory_to_decision(
    decision: RouterDecision,
    advisories: List[AdvisoryOutput]
) -> RouterDecision:
    """Attach advisory suggestions to a decision (post-decision only)."""
    overlay = RouterAdvisoryOverlay()
    return overlay.attach_advisory(decision, advisories)
