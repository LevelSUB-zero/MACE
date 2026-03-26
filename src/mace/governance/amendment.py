"""
Module: amendment
Stage: cross-stage
Purpose: Governance amendment engine. Loads policy amendments and enforces them
         with a fail-halt (kill-switch) strategy per the Zero Divergence Protocol.

Part of MACE (Meta Aware Cognitive Engine).
"""
import json
import logging
import os

AMENDMENTS_FILE = "amendments.jsonl"

logger = logging.getLogger(__name__)


class GovernanceViolation(Exception):
    """Raised when a critical governance policy is violated or corrupted."""


def load_amendments() -> list:
    """
    Load active amendments from file.

    Returns:
        list: Active amendment dicts.

    Raises:
        GovernanceViolation: If the amendments file exists but is corrupt
                             (fail-halt, NOT fail-open).
    """
    amendments = []
    if not os.path.exists(AMENDMENTS_FILE):
        return amendments

    try:
        with open(AMENDMENTS_FILE, "r") as f:
            for line_num, line in enumerate(f, 1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    amendments.append(json.loads(stripped))
                except json.JSONDecodeError as e:
                    # FAIL-HALT: Corrupt governance data is a critical violation
                    raise GovernanceViolation(
                        f"GOVERNANCE_CORRUPT: Malformed amendment at line {line_num} "
                        f"in {AMENDMENTS_FILE}: {e}"
                    )
    except GovernanceViolation:
        raise  # Re-raise governance violations
    except OSError as e:
        # FAIL-HALT: If we cannot read governance, we cannot enforce it
        raise GovernanceViolation(
            f"GOVERNANCE_UNREADABLE: Cannot read {AMENDMENTS_FILE}: {e}"
        )

    return amendments


def check_policy(policy_type: str, target: str) -> bool:
    """
    Check if a target is blocked by any active amendment.

    Args:
        policy_type: "block_key", "block_agent", etc.
        target: The value to check (e.g. key name).

    Returns:
        True if BLOCKED, False if ALLOWED.

    Raises:
        GovernanceViolation: If amendments cannot be loaded (fail-halt).
    """
    amendments = load_amendments()
    for amd in amendments:
        if not amd.get("active", True):
            continue

        if amd.get("policy_type") == policy_type:
            if amd.get("target") == target:
                return True

    return False
