"""
Module: meta_cognition_guard
Stage: 3
Purpose: Enforces reflection-without-control constraints. Validates parity
         between advisory and non-advisory runs, and screens reflective
         artifacts for forbidden self-modification attempts.

Part of MACE (Meta Aware Cognitive Engine).
Spec: docs/phase3/advisory_system_spec.md § 3.5
"""

from typing import Dict, Any
from dataclasses import dataclass

from mace.core import canonical
from mace.stage3 import advisory_events
from mace.stage3.advice_schema import Stage3SignedObject
from mace.stage3.constants import ESCALATION_VIOLATION_THRESHOLD


FORBIDDEN_REFLECTION_KEYS = [
    "override_router",
    "bypass_council",
    "force_action",
    "disable_governance",
    "trigger_retrain",
    "inject_memory"
]


@dataclass
class ReflectiveArtifact(Stage3SignedObject):
    """A signed reflective artifact produced by an advisory agent."""
    artifact_id: str
    source_module: str
    reflection_content: Dict[str, Any]
    created_seeded_ts: str


def validate_reflective_artifact(artifact: ReflectiveArtifact) -> bool:
    """
    Validate a reflective artifact for forbidden keys and signature integrity.

    Checks (MC-2):
        1. HMAC signature must be valid.
        2. No forbidden reflection keys at any nesting depth.

    On failure, emits REFLECTIVE_VIOLATION and triggers escalation check (MC-5).

    Returns:
        True if the artifact is safe, False otherwise.
    """
    if not artifact.verify():
        return False

    def _check_keys(obj: Any) -> bool:
        """Recursively check for forbidden keys in nested structures."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in FORBIDDEN_REFLECTION_KEYS:
                    return False
                if not _check_keys(v):
                    return False
        elif isinstance(obj, list):
            for item in obj:
                if not _check_keys(item):
                    return False
        return True

    is_valid = _check_keys(artifact.reflection_content)

    if not is_valid:
        advisory_events.append_advisory_event(
            "REFLECTIVE_VIOLATION",
            "meta_cognition_guard",
            {
                "artifact_id": artifact.artifact_id,
                "source": artifact.source_module,
                "reason": "Forbidden reflection keys detected."
            }
        )
        _handle_escalation(artifact.source_module)

    return is_valid


def _handle_escalation(source_module: str) -> None:
    """
    MC-5: Repeated offender escalation to MODULE_POLICY_VIOLATION.

    If a source module accumulates >= ESCALATION_VIOLATION_THRESHOLD
    reflective violations, a MODULE_POLICY_VIOLATION is emitted.
    """
    events = advisory_events.get_events_by_type("REFLECTIVE_VIOLATION")
    agent_violations = [
        e for e in events
        if e["payload"].get("source") == source_module
    ]

    if len(agent_violations) >= ESCALATION_VIOLATION_THRESHOLD:
        advisory_events.append_advisory_event(
            "MODULE_POLICY_VIOLATION",
            "meta_cognition_guard",
            {
                "source_module": source_module,
                "reason": (
                    f"Repeated offender: {len(agent_violations)} "
                    f"reflective violations."
                )
            }
        )


def parity_check(
    with_advice_result: Any,
    without_advice_result: Any,
    context_id: str
) -> bool:
    """
    MC-1: Compare output of a pipeline run with and without advice.

    If they differ, the advisory system is silently mutating execution
    behavior. Emits SILENT_INFLUENCE_ALERT on mismatch.

    Returns:
        True if outputs are identical (parity holds), False otherwise.
    """
    canon_with = canonical.canonical_json_serialize(with_advice_result)
    canon_without = canonical.canonical_json_serialize(without_advice_result)

    if canon_with != canon_without:
        advisory_events.append_advisory_event(
            "SILENT_INFLUENCE_ALERT",
            "meta_cognition_guard",
            {
                "context_id": context_id,
                "reason": (
                    "Parity check failed. Advisory input silently "
                    "changed deterministic behavior."
                )
            }
        )
        return False

    return True
