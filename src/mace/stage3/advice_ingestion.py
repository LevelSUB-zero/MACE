"""
Module: advice_ingestion
Stage: 3
Purpose: Validates incoming AdviceObjects at the ingestion boundary before
         they enter the Advisory Pipeline.

Part of MACE (Meta Aware Cognitive Engine).
Spec: docs/phase3/advisory_system_spec.md § 3.4
"""

from typing import Optional

from mace.stage3.advice_schema import AdviceObject
from mace.stage3.advice_quality import evaluate_advice, AdviceQualityReport
from mace.stage3 import advisory_events
from mace.stage3.constants import FORBIDDEN_TOKENS


def validate_advice_object(advice: AdviceObject) -> bool:
    """
    Validate the input advice object for integrity and policy compliance.

    Checks:
        1. HMAC signature is valid and untouched.
        2. Content contains no forbidden tokens from the shared deny-list.

    Returns:
        True if the advice passes all boundary checks, False otherwise.
    """
    # 1. Signature Check
    if not advice.verify():
        return False

    # 2. Forbidden Tokens Check
    content_lower = advice.content.lower()
    for token in FORBIDDEN_TOKENS:
        if token.lower() in content_lower:
            return False

    return True


def ingest_advice(
    advice: AdviceObject,
    query_fingerprint: str = "",
    historical_index: Optional[dict] = None
) -> Optional[AdviceQualityReport]:
    """
    Ingest advice into the Stage 3 Advisory System.

    If the advice fails the boundary check, emits a MODULE_POLICY_VIOLATION
    event and returns None. If it passes, runs quality evaluation and
    returns the resulting AdviceQualityReport.

    Returns:
        An AdviceQualityReport on success, or None on boundary failure.
    """
    historical_index = historical_index or {}

    if not validate_advice_object(advice):
        advisory_events.append_advisory_event(
            "MODULE_POLICY_VIOLATION",
            "advice_ingestion",
            {
                "advice_id": advice.advice_id,
                "reason": "Failed boundary validation (signature or forbidden token)",
                "content_snippet": advice.content[:100]
            },
            advice.evidence_refs
        )
        return None

    # Success path: emit ingested event first
    advisory_events.append_advisory_event(
        "ADVICE_INGESTED",
        "advice_ingestion",
        {"advice_id": advice.advice_id},
        advice.evidence_refs
    )

    # Run quality evaluation
    return evaluate_advice(advice, query_fingerprint, historical_index)
