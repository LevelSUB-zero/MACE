"""
Module: permission_boundary
Stage: 3
Purpose: Enforces that Advisory and MEM-SNN outputs are strictly observational.
         Blocks command-oriented language in agent outputs.

Part of MACE (Meta Aware Cognitive Engine).
Spec: docs/phase3/advisory_system_spec.md § 3.4
"""

from typing import Tuple

from mace.stage3 import advisory_events
from mace.stage3.constants import FORBIDDEN_OUTPUT_PATTERNS


def is_forbidden_output(output: str) -> bool:
    """
    Check if the raw string output contains any forbidden control tokens.

    Uses case-insensitive matching against the shared FORBIDDEN_OUTPUT_PATTERNS
    constant from constants.py (single source of truth).

    Returns:
        True if any forbidden pattern is found, False otherwise.
    """
    out_lower = output.lower()

    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        if pattern.lower() in out_lower:
            return True

    return False


def check_output_allowed(output: str, source_id: str) -> Tuple[bool, str]:
    """
    Check if an agent's output string is allowed under the permission boundary.

    If not allowed, emits a MODULE_POLICY_VIOLATION event to the advisory
    event log.

    Returns:
        A tuple of (is_allowed, reason).
    """
    if is_forbidden_output(output):
        reason = "Output contained forbidden control tokens. State mutation is restricted."
        advisory_events.append_advisory_event(
            "MODULE_POLICY_VIOLATION",
            "permission_boundary",
            {
                "source_id": source_id,
                "reason": reason,
                "snippet": output[:100]
            }
        )
        return False, reason

    return True, "Allowed"
