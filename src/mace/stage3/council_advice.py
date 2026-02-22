"""
Council Advice Review - Stage-3 Council Role Evolution

Council remains NON-EXECUTIVE.

In Stage-3, the Council gains exactly one new responsibility:
> Evaluate the quality of advice, not the quality of outcomes.

Council MAY:
- Score advisory usefulness
- Flag systematic advisory bias
- Preserve disagreement

Council may NOT:
- Accept advice
- Reject advice
- Act on advice
- Suppress advice

CouncilAdviceReview objects are LABELS, not DIRECTIVES.

Spec: docs/stage3/EXECUTION_PLAN_FINAL.md section 2.3
Spec: docs/stage3/advisory_system_spec.md section 3.3
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from .advisory_output import AdvisoryOutput


class AdviceUsefulnessScore(str, Enum):
    """
    Textual usefulness score for advice.
    These are LABELS, not numeric scores.
    """
    NOT_USEFUL = "not_useful"
    MARGINALLY_USEFUL = "marginally_useful"
    USEFUL = "useful"
    VERY_USEFUL = "very_useful"


class AdvisoryBiasFlag(str, Enum):
    """Flags for systematic advisory bias."""
    NO_BIAS = "no_bias"
    OPTIMISTIC_BIAS = "optimistic_bias"     # Consistently over-confident
    PESSIMISTIC_BIAS = "pessimistic_bias"   # Consistently under-confident
    SYSTEMATIC_ERROR = "systematic_error"    # Repeating same type of error
    INSUFFICIENT_DATA = "insufficient_data"  # Not enough data to assess


@dataclass
class CouncilAdviceReview:
    """
    Council's review of an advisory output.
    
    This is a LABEL, not a DIRECTIVE.
    Council cannot accept, reject, act on, or suppress advice.
    """
    review_id: str
    advisory_id: str
    job_seed: str
    
    # Usefulness assessment (textual label only)
    usefulness_score: AdviceUsefulnessScore = AdviceUsefulnessScore.MARGINALLY_USEFUL
    usefulness_rationale: str = ""
    
    # Bias detection
    bias_flag: AdvisoryBiasFlag = AdvisoryBiasFlag.NO_BIAS
    bias_rationale: str = ""
    
    # Disagreement preservation
    council_disagreed: bool = False
    disagreement_details: str = ""
    dissenting_members: List[str] = field(default_factory=list)
    
    # Metadata
    reviewed_by: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    immutable_signature: str = ""
    
    def __post_init__(self):
        if not self.review_id:
            self.review_id = self._generate_review_id()
        if not self.immutable_signature:
            self.immutable_signature = self._compute_signature()
    
    def _generate_review_id(self) -> str:
        content = f"{self.job_seed}:council_review:{self.advisory_id}:{self.created_at}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _compute_signature(self) -> str:
        import json
        canonical = json.dumps({
            "advisory_id": self.advisory_id,
            "usefulness_score": self.usefulness_score.value,
            "bias_flag": self.bias_flag.value,
            "council_disagreed": self.council_disagreed,
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "advisory_id": self.advisory_id,
            "job_seed": self.job_seed,
            "usefulness_score": self.usefulness_score.value,
            "usefulness_rationale": self.usefulness_rationale,
            "bias_flag": self.bias_flag.value,
            "bias_rationale": self.bias_rationale,
            "council_disagreed": self.council_disagreed,
            "disagreement_details": self.disagreement_details,
            "dissenting_members": self.dissenting_members,
            "reviewed_by": self.reviewed_by,
            "created_at": self.created_at,
            "immutable_signature": self.immutable_signature,
        }


@dataclass
class AdviceQualityReport:
    """
    Quality report for advisory output.
    
    Per spec: docs/stage3/advisory_system_spec.md section 3.3
    
    Metrics are for council visibility only.
    Composite thresholds are only used to suggest human attention (alerts) —
    they do not cause automated state changes.
    """
    report_id: str
    advisory_id: str
    job_seed: str
    
    # Quality metrics (deterministic, canonicalized)
    metrics: Dict[str, Any] = field(default_factory=lambda: {
        "F": 0.5,  # Factuality
        "R": 0.5,  # Relevance
        "C": 1.0,  # Coherence
        "P": 0.5,  # Provenance Strength
        "U": 1.0,  # Uncertainty Transparency
        "N": 0.5,  # Novelty
        "S": "safe",  # Safety
        "E": None,  # Empirical Utility (optional)
    })
    
    # Composite score (for council visibility only)
    composite_score: float = 0.0
    
    # Flags derived from metrics
    flags: List[str] = field(default_factory=list)
    
    # Evidence
    derived_from_evidence: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "advisory_id": self.advisory_id,
            "job_seed": self.job_seed,
            "metrics": self.metrics,
            "composite_score": self.composite_score,
            "flags": self.flags,
            "derived_from_evidence": self.derived_from_evidence,
            "created_at": self.created_at,
        }


class CouncilAdviceReviewer:
    """
    Manages council review of advisory outputs.
    
    Council evaluates the QUALITY of advice, not the quality of outcomes.
    Council cannot act on, accept, or reject advice.
    """
    
    def __init__(self):
        self._reviews: List[CouncilAdviceReview] = []
        self._quality_reports: List[AdviceQualityReport] = []
    
    def create_review(
        self,
        advisory: AdvisoryOutput,
        usefulness: AdviceUsefulnessScore,
        usefulness_rationale: str,
        reviewed_by: List[str]
    ) -> CouncilAdviceReview:
        """Create a council review for an advisory."""
        review = CouncilAdviceReview(
            review_id="",
            advisory_id=advisory.advisory_id,
            job_seed=advisory.job_seed,
            usefulness_score=usefulness,
            usefulness_rationale=usefulness_rationale,
            reviewed_by=reviewed_by,
        )
        self._reviews.append(review)
        return review
    
    def flag_bias(
        self,
        review_id: str,
        bias_flag: AdvisoryBiasFlag,
        bias_rationale: str
    ) -> bool:
        """Flag systematic bias in advisory."""
        for review in self._reviews:
            if review.review_id == review_id:
                review.bias_flag = bias_flag
                review.bias_rationale = bias_rationale
                return True
        return False
    
    def record_disagreement(
        self,
        review_id: str,
        disagreement_details: str,
        dissenting_members: List[str]
    ) -> bool:
        """Record council disagreement (preserved, not resolved)."""
        for review in self._reviews:
            if review.review_id == review_id:
                review.council_disagreed = True
                review.disagreement_details = disagreement_details
                review.dissenting_members = dissenting_members
                return True
        return False
    
    def compute_quality_report(
        self,
        advisory: AdvisoryOutput,
        evidence_refs: List[str]
    ) -> AdviceQualityReport:
        """
        Compute quality report for advisory.
        
        Metrics are for council visibility only.
        """
        report_id = hashlib.sha256(
            f"quality:{advisory.advisory_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Compute basic metrics (simplified for initial implementation)
        metrics = {
            "F": 0.5,  # Factuality - would need claim verification
            "R": 0.5,  # Relevance - would need context matching
            "C": 1.0,  # Coherence - assume coherent for now
            "P": 0.5 if evidence_refs else 0.2,  # Provenance
            "U": 1.0 if advisory.confidence_estimate else 0.0,  # Uncertainty transparency
            "N": 0.5,  # Novelty - would need historical comparison
            "S": "safe",  # Safety - assume safe unless flagged
            "E": None,  # Empirical utility - retroactive
        }
        
        # Compute composite (for council visibility only)
        weights = {"F": 0.25, "R": 0.20, "C": 0.15, "P": 0.15, "U": 0.10, "N": 0.05}
        composite = sum(
            weights.get(k, 0) * (v if isinstance(v, (int, float)) else 0.5)
            for k, v in metrics.items()
            if k in weights
        )
        
        # Flag detection
        flags = []
        if metrics.get("F", 0.5) <= 0.25 and metrics.get("P", 0.5) <= 0.4:
            flags.append("MISLEADING_ADVICE_FLAG")
        if metrics.get("P", 0.5) <= 0.35 and metrics.get("N", 0.5) >= 0.8:
            flags.append("PREMATURE_ADVICE_FLAG")
        
        report = AdviceQualityReport(
            report_id=report_id,
            advisory_id=advisory.advisory_id,
            job_seed=advisory.job_seed,
            metrics=metrics,
            composite_score=composite,
            flags=flags,
            derived_from_evidence=evidence_refs,
        )
        
        self._quality_reports.append(report)
        return report
    
    def get_reviews(self) -> List[CouncilAdviceReview]:
        """Get all reviews."""
        return self._reviews.copy()
    
    def get_quality_reports(self) -> List[AdviceQualityReport]:
        """Get all quality reports."""
        return self._quality_reports.copy()
