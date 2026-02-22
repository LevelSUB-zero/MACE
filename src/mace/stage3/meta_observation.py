"""
MetaObservation - Stage-3 Core Schema

A MetaObservation records counterfactual awareness:
- What advice suggested
- What actually happened
- How often advice was wrong

This is where meta-cognition actually begins.
These are DESCRIPTIVE, never PRESCRIPTIVE.

Spec: docs/stage3/EXECUTION_PLAN_FINAL.md section 3.1
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json


class DivergenceType(str, Enum):
    """Type of divergence between advice and actual outcome."""
    ROUTE_IGNORED = "route_ignored"           # Advice suggested alternate route; router ignored
    PREDICTION_WRONG = "prediction_wrong"     # Advice predicted X; outcome was Y
    REPAIR_AVOIDED = "repair_avoided"         # Advice would have reduced repair loops
    COUNCIL_DISAGREED = "council_disagreed"   # Advice predicted council rejection; council approved
    MEMORY_DIVERGED = "memory_diverged"       # Advice memory suggestion diverged from actual
    NO_DIVERGENCE = "no_divergence"           # Advice matched actual outcome


class ImpactEstimate(str, Enum):
    """
    Estimated impact of the divergence.
    These are TEXTUAL LABELS only - NOT numeric scores.
    """
    NEGLIGIBLE = "negligible"    # No meaningful difference
    MINOR = "minor"              # Small difference, same outcome
    MODERATE = "moderate"        # Noticeable difference
    SIGNIFICANT = "significant"  # Material difference in behavior


@dataclass
class MetaObservation:
    """
    The core meta-cognition artifact for Stage-3.
    
    Records counterfactual awareness:
    - What the system suggested it would do
    - What actually happened
    - How often the system was wrong
    
    Invariants:
    - These are DESCRIPTIVE, never PRESCRIPTIVE
    - Meta-cognition creates self-awareness of error, NOT self-correction
    - No self-rewriting, parameter tuning, threshold adjustment, or architecture modification
    
    Spec: docs/stage3/EXECUTION_PLAN_FINAL.md section 3.2
    """
    
    # Core identity
    observation_id: str
    job_seed: str
    
    # Link to advisory
    advisory_id: str
    advisory_content_summary: str
    
    # Actual outcome
    actual_outcome: str
    actual_outcome_details: Dict[str, Any] = field(default_factory=dict)
    
    # Divergence analysis
    divergence_type: DivergenceType = DivergenceType.NO_DIVERGENCE
    divergence_description: str = ""
    
    # Impact (textual label only)
    impact_estimate: ImpactEstimate = ImpactEstimate.NEGLIGIBLE
    
    # Evidence and context
    evidence_refs: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_seed: str = ""
    
    # Signature
    immutable_signature: str = ""
    
    def __post_init__(self):
        """Validate and compute derived fields."""
        if not self.observation_id:
            self.observation_id = self._generate_observation_id()
        if not self.created_seed:
            self.created_seed = self.job_seed
        if not self.immutable_signature:
            self.immutable_signature = self._compute_signature()
    
    def _generate_observation_id(self) -> str:
        """Generate deterministic observation ID."""
        content = f"{self.job_seed}:meta:{self.advisory_id}:{self.divergence_type.value}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _compute_signature(self) -> str:
        """Compute HMAC signature for immutability."""
        canonical = self.to_canonical_json()
        return hashlib.sha256(canonical.encode()).hexdigest()[:32]
    
    def to_canonical_json(self) -> str:
        """Canonical JSON serialization."""
        return json.dumps({
            "observation_id": self.observation_id,
            "job_seed": self.job_seed,
            "advisory_id": self.advisory_id,
            "advisory_content_summary": self.advisory_content_summary,
            "actual_outcome": self.actual_outcome,
            "divergence_type": self.divergence_type.value,
            "divergence_description": self.divergence_description,
            "impact_estimate": self.impact_estimate.value,
            "evidence_refs": sorted(self.evidence_refs),
        }, sort_keys=True, separators=(',', ':'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "observation_id": self.observation_id,
            "job_seed": self.job_seed,
            "advisory_id": self.advisory_id,
            "advisory_content_summary": self.advisory_content_summary,
            "actual_outcome": self.actual_outcome,
            "actual_outcome_details": self.actual_outcome_details,
            "divergence_type": self.divergence_type.value,
            "divergence_description": self.divergence_description,
            "impact_estimate": self.impact_estimate.value,
            "evidence_refs": self.evidence_refs,
            "context": self.context,
            "created_at": self.created_at,
            "created_seed": self.created_seed,
            "immutable_signature": self.immutable_signature,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetaObservation":
        """Reconstruct from dictionary."""
        return cls(
            observation_id=data.get("observation_id", ""),
            job_seed=data["job_seed"],
            advisory_id=data["advisory_id"],
            advisory_content_summary=data["advisory_content_summary"],
            actual_outcome=data["actual_outcome"],
            actual_outcome_details=data.get("actual_outcome_details", {}),
            divergence_type=DivergenceType(data.get("divergence_type", "no_divergence")),
            divergence_description=data.get("divergence_description", ""),
            impact_estimate=ImpactEstimate(data.get("impact_estimate", "negligible")),
            evidence_refs=data.get("evidence_refs", []),
            context=data.get("context", {}),
            created_at=data.get("created_at", ""),
            created_seed=data.get("created_seed", ""),
            immutable_signature=data.get("immutable_signature", ""),
        )
    
    def has_divergence(self) -> bool:
        """Check if there is any divergence between advice and outcome."""
        return self.divergence_type != DivergenceType.NO_DIVERGENCE
    
    def verify_signature(self) -> bool:
        """Verify immutable signature."""
        expected = hashlib.sha256(self.to_canonical_json().encode()).hexdigest()[:32]
        return self.immutable_signature == expected


# Factory functions for common meta-observations
def create_route_ignored_observation(
    job_seed: str,
    advisory_id: str,
    advised_route: str,
    actual_route: str,
    evidence_refs: List[str]
) -> MetaObservation:
    """Create observation when router ignored advice."""
    return MetaObservation(
        observation_id="",
        job_seed=job_seed,
        advisory_id=advisory_id,
        advisory_content_summary=f"Advised route: {advised_route}",
        actual_outcome=f"Actual route: {actual_route}",
        actual_outcome_details={"advised": advised_route, "actual": actual_route},
        divergence_type=DivergenceType.ROUTE_IGNORED,
        divergence_description=f"Advice suggested route '{advised_route}'; router chose '{actual_route}'",
        impact_estimate=ImpactEstimate.MINOR,
        evidence_refs=evidence_refs,
    )


def create_council_disagreement_observation(
    job_seed: str,
    advisory_id: str,
    predicted_decision: str,
    actual_decision: str,
    evidence_refs: List[str]
) -> MetaObservation:
    """Create observation when council disagreed with advice prediction."""
    return MetaObservation(
        observation_id="",
        job_seed=job_seed,
        advisory_id=advisory_id,
        advisory_content_summary=f"Predicted council decision: {predicted_decision}",
        actual_outcome=f"Actual council decision: {actual_decision}",
        actual_outcome_details={"predicted": predicted_decision, "actual": actual_decision},
        divergence_type=DivergenceType.COUNCIL_DISAGREED,
        divergence_description=f"Advice predicted '{predicted_decision}'; council decided '{actual_decision}'",
        impact_estimate=ImpactEstimate.MODERATE,
        evidence_refs=evidence_refs,
    )


def create_no_divergence_observation(
    job_seed: str,
    advisory_id: str,
    matched_outcome: str,
    evidence_refs: List[str]
) -> MetaObservation:
    """Create observation when advice matched actual outcome."""
    return MetaObservation(
        observation_id="",
        job_seed=job_seed,
        advisory_id=advisory_id,
        advisory_content_summary=f"Advised: {matched_outcome}",
        actual_outcome=f"Actual: {matched_outcome}",
        divergence_type=DivergenceType.NO_DIVERGENCE,
        divergence_description="Advice matched actual outcome",
        impact_estimate=ImpactEstimate.NEGLIGIBLE,
        evidence_refs=evidence_refs,
    )
