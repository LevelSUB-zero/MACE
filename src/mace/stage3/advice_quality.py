"""
Module: advice_quality
Stage: 3
Purpose: Deterministic quality metric computation for advisory content.
         Calculates heuristic metrics and emits advisory flag events
         when thresholds are breached.

Part of MACE (Meta Aware Cognitive Engine).
Spec: docs/phase3/advisory_system_spec.md § 3.3
"""

from typing import List, Any, Optional
from mace.core import deterministic
from mace.stage3.advice_schema import AdviceObject, AdviceQualityReport
from mace.stage3 import advisory_events


def compute_factuality(claims: str, evidence_refs: List[str]) -> float:
    """
    Compute a factuality score based on evidence backing.

    # PLACEHOLDER: Replace with cognitive heuristic in Stage 5.
    Currently uses keyword detection as a deterministic proxy.

    Returns:
        A float in [0, 1] where 1.0 = fully supported by evidence.
    """
    if "inaccurate" in claims.lower():
        return 0.2
    return 0.8 if evidence_refs else 0.5


def compute_relevance(query_fingerprint: str, evidence_refs: List[str]) -> float:
    """
    Compute relevance of advice to the original query context.

    # PLACEHOLDER: Replace with cognitive heuristic in Stage 5.

    Returns:
        A float in [0, 1] where 1.0 = fully relevant.
    """
    return 0.9 if evidence_refs else 0.1


def compute_coherence(content: str) -> float:
    """
    Compute coherence of the advice content.

    # PLACEHOLDER: Replace with cognitive heuristic in Stage 5.
    Returns 0.0 for incoherent, 0.5 for partially coherent,
    1.0 for fully coherent content.

    Returns:
        A float in {0.0, 0.5, 1.0}.
    """
    if "incoherent" in content.lower():
        return 0.0
    if "partial" in content.lower() or "unclear" in content.lower():
        return 0.5
    return 1.0


def compute_provenance(evidence_refs: List[str], content: str = "") -> float:
    """
    Compute provenance score based on evidence trail.

    # PLACEHOLDER: Replace with cognitive heuristic in Stage 5.

    Returns:
        A float in [0, 1] where 1.0 = strong evidence lineage.
    """
    if "baseless" in content.lower():
        return 0.2
    return 0.9 if len(evidence_refs) > 0 else 0.1


def compute_uncertainty(advice: str) -> float:
    """
    Compute expressed uncertainty in the advice.

    # PLACEHOLDER: Replace with cognitive heuristic in Stage 5.

    Returns:
        A float in {0.0, 0.2, 1.0} where 0.0 = assertive/certain.
    """
    if "maybe" in advice.lower():
        return 1.0
    if "assertive" in advice.lower() or "must" in advice.lower():
        return 0.0
    return 0.2


def compute_novelty(advice: str, historical_index: Any) -> float:
    """
    Compute how novel the advice is compared to historical context.

    # PLACEHOLDER: Replace with cognitive heuristic in Stage 5.

    Returns:
        A float in [0, 1] where 1.0 = highly novel.
    """
    if "novel" in advice.lower():
        return 0.9
    return 0.1


def compute_empirical_utility(advice: str) -> float:
    """
    Compute the empirical utility of the advice based on past outcomes.

    # PLACEHOLDER: Replace with cognitive heuristic in Stage 5.

    Returns:
        A float in [0, 1] where 1.0 = highly useful.
    """
    return 0.5


def compute_composite(
    metrics: List[float],
    weights: Optional[List[float]] = None
) -> float:
    """
    Compute a weighted composite score from individual metrics.

    Returns:
        A float in [0, 1] representing the overall quality score.
        Returns 0.0 for empty metrics or all-zero weights.
    """
    if not metrics:
        return 0.0
    if not weights:
        weights = [1.0] * len(metrics)
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    return sum(m * w for m, w in zip(metrics, weights)) / total_w


def evaluate_advice(
    advice: AdviceObject,
    query_fingerprint: str,
    historical_index: Any
) -> AdviceQualityReport:
    """
    Evaluate advice and produce a quality report, emitting flag events
    if quality thresholds are breached.

    Returns:
        A signed AdviceQualityReport with all computed metrics and flags.
    """
    f = compute_factuality(advice.content, advice.evidence_refs)
    r = compute_relevance(query_fingerprint, advice.evidence_refs)
    c = compute_coherence(advice.content)
    p = compute_provenance(advice.evidence_refs, advice.content)
    u = compute_uncertainty(advice.content)
    n = compute_novelty(advice.content, historical_index)
    s = "unsafe" if "unsafe" in advice.content.lower() else "safe"
    e = compute_empirical_utility(advice.content)

    comp = compute_composite([f, r, c, p, (1.0 - u), n, e])
    flags: List[str] = []

    # MISLEADING_CANDIDATE if F <= 0.25 AND P <= 0.4 AND not U (u == 0)
    if f <= 0.25 and p <= 0.4 and u == 0.0:
        flags.append("MISLEADING_ADVICE")
        advisory_events.append_advisory_event(
            "MISLEADING_ADVICE_FLAG",
            "advice_quality",
            {"advice_id": advice.advice_id, "F": f, "P": p, "U": u},
            advice.evidence_refs
        )

    # PREMATURE_ADVICE if P <= 0.35 AND N >= 0.8 AND not U (u == 0)
    if p <= 0.35 and n >= 0.8 and u == 0.0:
        flags.append("PREMATURE_ADVICE")
        advisory_events.append_advisory_event(
            "PREMATURE_ADVICE_FLAG",
            "advice_quality",
            {"advice_id": advice.advice_id, "P": p, "N": n, "U": u},
            advice.evidence_refs
        )

    # SAFETY_CONCERN if S == "unsafe" or PII present
    if s == "unsafe" or "PII" in advice.content.upper():
        flags.append("SAFETY_CONCERN")
        advisory_events.append_advisory_event(
            "SAFETY_ADVICE_FLAG",
            "advice_quality",
            {"advice_id": advice.advice_id, "safety": s},
            advice.evidence_refs
        )

    seed = deterministic.get_seed() or "eval_fallback"
    if deterministic.get_seed() is None:
        deterministic.init_seed(seed)

    report_id = deterministic.deterministic_id("quality_report", advice.advice_id)
    report_ts = deterministic.deterministic_id("quality_tick", report_id)

    report = AdviceQualityReport(
        report_id=report_id,
        advice_id=advice.advice_id,
        factuality=f,
        relevance=r,
        coherence=c,
        provenance=p,
        uncertainty=u,
        novelty=n,
        safety=s,
        empirical_utility=e,
        composite_score=comp,
        flags=flags,
        created_seeded_ts=report_ts,
        derived_from_evidence=len(advice.evidence_refs) > 0
    )
    report.sign()

    advisory_events.append_advisory_event(
        "ADVICE_QUALITY_REPORT",
        "advice_quality",
        report.to_dict(),
        advice.evidence_refs
    )

    return report
