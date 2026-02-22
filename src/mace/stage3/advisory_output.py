"""
AdvisoryOutput - Stage-3 Core Schema

Advisory is not "extra data". It is a formally bounded cognitive artifact.
AdvisoryOutput has no executable semantics, no side effects, and must be safe to delete.

Spec: docs/stage3/EXECUTION_PLAN_FINAL.md section 2.1
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json


class AdvisoryType(str, Enum):
    """
    Allowed advisory types per Stage-3 Advisory Ontology.
    Spec: docs/stage3/advisory_system_spec.md section 4
    """
    ROUTING_SUGGESTION = "routing_suggestion"
    RISK_NOTE = "risk_note"
    CONFIDENCE_ANNOTATION = "confidence_annotation"
    SIMILARITY_HINT = "similarity_hint"
    ANOMALY_REPORT = "anomaly_report"
    RETROSPECTIVE_SUMMARY = "retrospective_summary"
    SUGGESTED_TEST = "suggested_test"
    HUMAN_ACTION_RECOMMENDATION = "human_action_recommendation"


class AdvisoryScope(str, Enum):
    """Scope of the advisory output."""
    ROUTER = "router"
    MEMORY = "memory"
    COUNCIL = "council"


class SuggestionType(str, Enum):
    """Type of suggestion payload."""
    RANK = "rank"
    ALTERNATIVE = "alternative"
    CONFIDENCE_DELTA = "confidence_delta"
    SIMILARITY_REFERENCE = "similarity_reference"


class AdvisoryConfidence(str, Enum):
    """
    Advisory confidence as textual labels ONLY.
    These are ANNOTATIONS, not SIGNALS.
    They MUST NOT be:
    - Combined with router confidence
    - Compared numerically
    - Thresholded
    - Aggregated
    """
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    UNCERTAIN = "uncertain"


@dataclass
class AdvisoryOutput:
    """
    The core advisory artifact for Stage-3.
    
    Invariants:
    - Has no executable semantics
    - Has no side effects
    - Must be safe to delete
    - If deleting all AdvisoryOutput objects changes system behavior → Stage-3 is invalid
    
    Temporal Containment:
    - Produced AFTER core execution
    - Produced BEFORE ReflectiveLog finalization
    - NEVER passed into router logic, agent execution, memory reads/writes, or council decision paths
    
    Persistence Containment:
    - NEVER persisted to SEM, episodic memory, CWM, or WM
    - Only durable existence is inside ReflectiveLog
    """
    
    # Core identity
    advisory_id: str
    source_model: str
    job_seed: str
    
    # Scope and type
    scope: AdvisoryScope
    advice_type: AdvisoryType
    suggestion_type: SuggestionType
    
    # Content (structured, not executable)
    suggestion_payload: Dict[str, Any]
    content: str  # Human-readable summary
    
    # Confidence (textual label only, NON-COMPARABLE)
    confidence_estimate: AdvisoryConfidence
    
    # Evidence linkage
    evidence_refs: List[str] = field(default_factory=list)
    
    # P0 Item 3: Advisory Generator Versioning
    # Required for historical log comparability
    generator_id: str = "mem-snn-shadow-v1"       # Generator identifier
    model_version: str = "2026-01-24-a"           # Model version
    scoring_method: str = "shadow"                 # "shadow" | "real" | "fallback"
    calibration_version: str = "v1.0"             # Confidence calibration version
    
    # Timestamps
    created_seed: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Signature for immutability
    immutable_signature: str = ""
    
    # Flag indicating this is advisory only
    advisory_only: bool = True

    
    def __post_init__(self):
        """Validate and compute derived fields."""
        if not self.advisory_id:
            self.advisory_id = self._generate_advisory_id()
        if not self.created_seed:
            self.created_seed = self.job_seed
        if not self.immutable_signature:
            self.immutable_signature = self._compute_signature()
    
    def _generate_advisory_id(self) -> str:
        """Generate deterministic advisory ID from job_seed."""
        content = f"{self.job_seed}:advice:{self.content[:50]}:{self.created_at}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _compute_signature(self) -> str:
        """Compute HMAC signature for immutability verification."""
        canonical = self.to_canonical_json()
        # In production, use HMAC with module key
        return hashlib.sha256(canonical.encode()).hexdigest()[:32]
    
    def to_canonical_json(self) -> str:
        """Canonical JSON serialization for signature and comparison."""
        return json.dumps({
            "advisory_id": self.advisory_id,
            "source_model": self.source_model,
            "job_seed": self.job_seed,
            "scope": self.scope.value if isinstance(self.scope, Enum) else self.scope,
            "advice_type": self.advice_type.value if isinstance(self.advice_type, Enum) else self.advice_type,
            "suggestion_type": self.suggestion_type.value if isinstance(self.suggestion_type, Enum) else self.suggestion_type,
            "suggestion_payload": self.suggestion_payload,
            "content": self.content,
            "confidence_estimate": self.confidence_estimate.value if isinstance(self.confidence_estimate, Enum) else self.confidence_estimate,
            "evidence_refs": sorted(self.evidence_refs),
            "created_seed": self.created_seed,
            # P0 versioning fields
            "generator_id": self.generator_id,
            "model_version": self.model_version,
            "scoring_method": self.scoring_method,
            "calibration_version": self.calibration_version,
        }, sort_keys=True, separators=(',', ':'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "advisory_id": self.advisory_id,
            "source_model": self.source_model,
            "job_seed": self.job_seed,
            "scope": self.scope.value if isinstance(self.scope, Enum) else self.scope,
            "advice_type": self.advice_type.value if isinstance(self.advice_type, Enum) else self.advice_type,
            "suggestion_type": self.suggestion_type.value if isinstance(self.suggestion_type, Enum) else self.suggestion_type,
            "suggestion_payload": self.suggestion_payload,
            "content": self.content,
            "confidence_estimate": self.confidence_estimate.value if isinstance(self.confidence_estimate, Enum) else self.confidence_estimate,
            "evidence_refs": self.evidence_refs,
            "created_seed": self.created_seed,
            "created_at": self.created_at,
            "immutable_signature": self.immutable_signature,
            "advisory_only": self.advisory_only,
            # P0 versioning fields
            "generator_id": self.generator_id,
            "model_version": self.model_version,
            "scoring_method": self.scoring_method,
            "calibration_version": self.calibration_version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdvisoryOutput":
        """Reconstruct from dictionary."""
        return cls(
            advisory_id=data.get("advisory_id", ""),
            source_model=data["source_model"],
            job_seed=data["job_seed"],
            scope=AdvisoryScope(data["scope"]),
            advice_type=AdvisoryType(data["advice_type"]),
            suggestion_type=SuggestionType(data["suggestion_type"]),
            suggestion_payload=data["suggestion_payload"],
            content=data["content"],
            confidence_estimate=AdvisoryConfidence(data["confidence_estimate"]),
            evidence_refs=data.get("evidence_refs", []),
            created_seed=data.get("created_seed", ""),
            created_at=data.get("created_at", ""),
            immutable_signature=data.get("immutable_signature", ""),
        )
    
    def verify_signature(self) -> bool:
        """Verify immutable signature matches content."""
        expected = hashlib.sha256(self.to_canonical_json().encode()).hexdigest()[:32]
        return self.immutable_signature == expected


# Convenience factory functions
def create_routing_suggestion(
    source_model: str,
    job_seed: str,
    content: str,
    evidence_refs: List[str],
    suggestion_payload: Dict[str, Any],
    confidence: AdvisoryConfidence = AdvisoryConfidence.MEDIUM
) -> AdvisoryOutput:
    """Create a routing suggestion advisory."""
    return AdvisoryOutput(
        advisory_id="",
        source_model=source_model,
        job_seed=job_seed,
        scope=AdvisoryScope.ROUTER,
        advice_type=AdvisoryType.ROUTING_SUGGESTION,
        suggestion_type=SuggestionType.RANK,
        suggestion_payload=suggestion_payload,
        content=content,
        confidence_estimate=confidence,
        evidence_refs=evidence_refs,
    )


def create_risk_note(
    source_model: str,
    job_seed: str,
    content: str,
    evidence_refs: List[str],
    severity: str = "medium"
) -> AdvisoryOutput:
    """Create a risk note advisory."""
    return AdvisoryOutput(
        advisory_id="",
        source_model=source_model,
        job_seed=job_seed,
        scope=AdvisoryScope.COUNCIL,
        advice_type=AdvisoryType.RISK_NOTE,
        suggestion_type=SuggestionType.ALTERNATIVE,
        suggestion_payload={"severity": severity},
        content=content,
        confidence_estimate=AdvisoryConfidence(severity) if severity in ["low", "medium", "high"] else AdvisoryConfidence.MEDIUM,
        evidence_refs=evidence_refs,
    )


def create_anomaly_report(
    source_model: str,
    job_seed: str,
    content: str,
    evidence_refs: List[str],
    anomaly_details: Dict[str, Any]
) -> AdvisoryOutput:
    """Create an anomaly report advisory."""
    return AdvisoryOutput(
        advisory_id="",
        source_model=source_model,
        job_seed=job_seed,
        scope=AdvisoryScope.ROUTER,
        advice_type=AdvisoryType.ANOMALY_REPORT,
        suggestion_type=SuggestionType.CONFIDENCE_DELTA,
        suggestion_payload=anomaly_details,
        content=content,
        confidence_estimate=AdvisoryConfidence.HIGH,
        evidence_refs=evidence_refs,
    )
