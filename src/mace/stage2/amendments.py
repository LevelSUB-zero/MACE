"""
Stage-2 Amendments (Delayed Rewards) (AUTHORITATIVE)

Purpose: Create temporal credit assignment without guessing.
Spec: docs/stage2_amendments.md

Core Doctrine:
- Amendments are append-only
- No reward inferred from SEM overwrite
- Only explicit amendments produce reward signals
- Backward linkage must be explicit (no heuristic guessing)
"""

import json
import datetime
from typing import Dict, Any, Optional, List

from mace.core import deterministic, canonical, persistence
from mace.stage2 import events


# =============================================================================
# AMENDMENT SCHEMA (APPEND-ONLY)
# =============================================================================

# Reason types for amendments
AMENDMENT_REASONS = [
    "correction",      # "What we thought was True is now False" → Strong negative
    "contradiction",   # "Evidence conflicts" → Uncertainty increase  
    "confirmation"     # "What we thought is still True" → Strong positive
]

# Schema version
AMENDMENT_SCHEMA_VERSION = "2.0"


def _validate_reason(reason: str) -> str:
    """Validate amendment reason is one of allowed values."""
    if reason not in AMENDMENT_REASONS:
        raise ValueError(
            f"Invalid amendment reason: '{reason}'. Must be one of {AMENDMENT_REASONS}"
        )
    return reason


def _validate_reward(reward: int) -> int:
    """Validate reward is -1 or +1."""
    if reward not in [-1, 1]:
        raise ValueError(
            f"Invalid reward: {reward}. Must be -1 or +1 (delayed reward signal)"
        )
    return reward


def create_amendment(
    original_candidate_id: str,
    delay_ticks: int,
    reward: int,
    reason: str,
    evidence_ids: List[str] = None,
    job_seed: str = None
) -> Dict[str, Any]:
    """
    Create an amendment (delayed reward) for a previous candidate.
    
    An amendment states: "What we thought earlier is no longer valid."
    
    Args:
        original_candidate_id: The candidate being amended
        delay_ticks: Time delta since original candidate
        reward: -1 (negative) or +1 (positive)
        reason: One of AMENDMENT_REASONS
        evidence_ids: Evidence supporting this amendment
        job_seed: For deterministic ID generation
    
    Returns:
        Amendment dict with deterministic ID
    """
    reason = _validate_reason(reason)
    reward = _validate_reward(reward)
    
    # Generate deterministic amendment ID
    seed = job_seed or deterministic.get_seed() or "amendment_fallback"
    if deterministic.get_seed() is None:
        deterministic.init_seed(seed)
    
    amendment_id = deterministic.deterministic_id(
        "stage2_amendment",
        f"{original_candidate_id}:{delay_ticks}:{reason}"
    )
    
    amendment = {
        "amendment_id": amendment_id,
        "original_candidate_id": original_candidate_id,
        "delay_ticks": delay_ticks,
        "reward": reward,
        "reason": reason,
        "evidence_ids": evidence_ids or [],
        "schema_version": AMENDMENT_SCHEMA_VERSION
    }
    
    return amendment


def persist_amendment(amendment: Dict[str, Any]) -> str:
    """
    Persist an amendment (APPEND-ONLY).
    Also logs an amendment event.
    
    Returns amendment_id.
    """
    conn = persistence.get_connection()
    try:
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        persistence.execute_query(conn,
            """INSERT INTO stage2_amendments 
               (amendment_id, original_candidate_id, delay_ticks, reward, reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                amendment["amendment_id"],
                amendment["original_candidate_id"],
                amendment["delay_ticks"],
                amendment["reward"],
                amendment["reason"],
                created_at
            )
        )
        conn.commit()
        
        # Log event
        events.log_amendment(
            amendment_id=amendment["amendment_id"],
            original_candidate_id=amendment["original_candidate_id"],
            delay_ticks=amendment["delay_ticks"],
            reward=amendment["reward"],
            reason=amendment["reason"],
            evidence_ids=amendment.get("evidence_ids", [])
        )
        
        return amendment["amendment_id"]
    finally:
        conn.close()


def get_amendments_for_candidate(candidate_id: str) -> List[Dict[str, Any]]:
    """
    Get all amendments that reference a specific candidate.
    Amendments are append-only, so there may be multiple.
    """
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn,
            """SELECT * FROM stage2_amendments 
               WHERE original_candidate_id = ? 
               ORDER BY created_at""",
            (candidate_id,)
        )
        amendments = []
        for row in persistence.fetch_all(cur):
            amendments.append({
                "amendment_id": row["amendment_id"],
                "original_candidate_id": row["original_candidate_id"],
                "delay_ticks": row["delay_ticks"],
                "reward": row["reward"],
                "reason": row["reason"]
            })
        return amendments
    finally:
        conn.close()


def compute_cumulative_reward(candidate_id: str) -> int:
    """
    Compute cumulative reward for a candidate from all its amendments.
    
    Returns:
        Sum of all reward signals (-1 or +1 each)
    """
    amendments = get_amendments_for_candidate(candidate_id)
    return sum(a["reward"] for a in amendments)


def has_amendments(candidate_id: str) -> bool:
    """Check if a candidate has been amended."""
    return len(get_amendments_for_candidate(candidate_id)) > 0


# =============================================================================
# WHAT DOES NOT COUNT (EXPLICIT)
# =============================================================================
# The following do NOT produce learning signals:
# - Overwrites (simple DB updates)
# - Decay (forgetting due to time)
# - Replacement (newer version without semantic link)
# - Silence (lack of re-verification)

def is_valid_amendment_trigger(trigger_type: str) -> bool:
    """
    Check if a trigger type is valid for creating an amendment.
    
    Only explicit amendments count. These do NOT count:
    - overwrite
    - decay
    - replacement
    - silence
    """
    invalid_triggers = ["overwrite", "decay", "replacement", "silence"]
    return trigger_type.lower() not in invalid_triggers


# =============================================================================
# BACKWARD LINKAGE VALIDATION
# =============================================================================

def validate_backward_linkage(
    amendment: Dict[str, Any],
    candidate_exists_fn: callable = None
) -> Dict[str, Any]:
    """
    Validate that an amendment has proper backward linkage.
    
    No heuristic back-propagation allowed.
    The link to original_candidate_id must be explicit.
    
    Returns:
        Validation result dict
    """
    issues = []
    
    # Check candidate ID is present
    if not amendment.get("original_candidate_id"):
        issues.append("Missing original_candidate_id - backward linkage required")
    
    # Check delay_ticks is valid
    delay = amendment.get("delay_ticks", -1)
    if delay < 0:
        issues.append("Invalid delay_ticks - must be >= 0")
    
    # Check candidate exists (if verification function provided)
    if candidate_exists_fn and amendment.get("original_candidate_id"):
        if not candidate_exists_fn(amendment["original_candidate_id"]):
            issues.append(f"Candidate {amendment['original_candidate_id']} does not exist")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues
    }
