"""
Stage-2 Council Label Generation (AUTHORITATIVE)

Purpose: Council becomes ground truth generator, not executor.
Spec: docs/stage2_council_labels.md

Core Doctrine:
- Council does NOT decide actions
- Council LABELS reality
- Conflicts are PRESERVED, not collapsed
- Labels are IMMUTABLE once finalized
"""

import json
import datetime
from typing import Dict, Any, List, Optional

from mace.core import deterministic, canonical, persistence
from mace.stage2 import events


# =============================================================================
# LABEL SCHEMA (IMMUTABLE)
# =============================================================================

# Label values for governance_label field
GOVERNANCE_LABELS = [
    "approved",
    "rejected",
    "conflict",
    "no_decision"
]

# Schema version
LABEL_SCHEMA_VERSION = "2.0"


def _validate_governance_label(label: str) -> str:
    """Validate governance label is one of allowed values."""
    if label not in GOVERNANCE_LABELS:
        raise ValueError(
            f"Invalid governance_label: '{label}'. Must be one of {GOVERNANCE_LABELS}"
        )
    return label


def create_council_label(
    candidate_id: str,
    truth_label: Optional[bool],
    safety_label: Optional[bool],
    utility_label: Optional[bool],
    governance_label: str,
    has_conflict: bool = False,
    job_seed: str = None
) -> Dict[str, Any]:
    """
    Create a council label for a candidate.
    
    Args:
        candidate_id: ID of the candidate being labeled
        truth_label: True/False/None (epistemic correctness)
        safety_label: True/False/None (harm potential)
        utility_label: True/False/None (future repair reduction)
        governance_label: One of GOVERNANCE_LABELS
        has_conflict: Whether council members disagreed
        job_seed: For deterministic ID generation
    
    Returns:
        Label dict with deterministic ID
    """
    governance_label = _validate_governance_label(governance_label)
    
    # Generate deterministic label ID
    seed = job_seed or deterministic.get_seed() or "label_fallback"
    if deterministic.get_seed() is None:
        deterministic.init_seed(seed)
    
    label_id = deterministic.deterministic_id(
        "council_label", 
        f"{candidate_id}:{governance_label}"
    )
    
    label = {
        "label_id": label_id,
        "candidate_id": candidate_id,
        "truth_label": truth_label,
        "safety_label": safety_label,
        "utility_label": utility_label,
        "governance_label": governance_label,
        "has_conflict": has_conflict,
        "schema_version": LABEL_SCHEMA_VERSION
    }
    
    return label


def persist_label(label: Dict[str, Any]) -> str:
    """
    Persist a council label (IMMUTABLE).
    Also logs a council_vote event.
    
    Returns label_id.
    """
    conn = persistence.get_connection()
    try:
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Convert bools to ints for SQLite
        truth_int = 1 if label["truth_label"] else (0 if label["truth_label"] is False else None)
        safety_int = 1 if label["safety_label"] else (0 if label["safety_label"] is False else None)
        utility_int = 1 if label["utility_label"] else (0 if label["utility_label"] is False else None)
        
        persistence.execute_query(conn,
            """INSERT INTO stage2_council_labels 
               (label_id, candidate_id, truth_label, safety_label, utility_label, 
                governance_label, has_conflict, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                label["label_id"],
                label["candidate_id"],
                truth_int,
                safety_int,
                utility_int,
                label["governance_label"],
                1 if label["has_conflict"] else 0,
                created_at
            )
        )
        conn.commit()
        
        # Log event
        events.log_council_vote(
            vote_id=label["label_id"],
            candidate_id=label["candidate_id"],
            labels={
                "truth": label["truth_label"],
                "safety": label["safety_label"],
                "utility": label["utility_label"],
                "governance": label["governance_label"],
                "conflict": label["has_conflict"]
            },
            job_seed=label.get("job_seed")
        )
        
        return label["label_id"]
    finally:
        conn.close()


def get_label_for_candidate(candidate_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the council label for a candidate.
    Labels are immutable - only one label per candidate.
    """
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn,
            "SELECT * FROM stage2_council_labels WHERE candidate_id = ?",
            (candidate_id,)
        )
        row = persistence.fetch_one(cur)
        if row:
            return {
                "label_id": row["label_id"],
                "candidate_id": row["candidate_id"],
                "truth_label": bool(row["truth_label"]) if row["truth_label"] is not None else None,
                "safety_label": bool(row["safety_label"]) if row["safety_label"] is not None else None,
                "utility_label": bool(row["utility_label"]) if row["utility_label"] is not None else None,
                "governance_label": row["governance_label"],
                "has_conflict": bool(row["has_conflict"])
            }
        return None
    finally:
        conn.close()


# =============================================================================
# CONFLICT HANDLING (PRESERVATION DOCTRINE)
# =============================================================================

def label_from_votes(
    candidate_id: str,
    votes: List[Dict[str, Any]],
    job_seed: str = None
) -> Dict[str, Any]:
    """
    Create a council label from multiple council member votes.
    
    Conflict Preservation Doctrine:
    - Conflicts remain visible
    - Never collapsed or averaged
    - Never resolved automatically
    
    Args:
        candidate_id: ID of candidate
        votes: List of vote dicts from council members
        job_seed: For deterministic ID
    
    Returns:
        Aggregated label with conflict flag
    """
    if not votes:
        return create_council_label(
            candidate_id=candidate_id,
            truth_label=None,
            safety_label=None,
            utility_label=None,
            governance_label="no_decision",
            has_conflict=False,
            job_seed=job_seed
        )
    
    # Check for conflicts (any disagreement)
    truth_values = [v.get("truth") for v in votes if v.get("truth") is not None]
    safety_values = [v.get("safety") for v in votes if v.get("safety") is not None]
    utility_values = [v.get("utility") for v in votes if v.get("utility") is not None]
    governance_values = [v.get("governance") for v in votes if v.get("governance")]
    
    has_conflict = (
        len(set(truth_values)) > 1 or
        len(set(safety_values)) > 1 or
        len(set(utility_values)) > 1 or
        len(set(governance_values)) > 1
    )
    
    # If conflict exists, governance_label = "conflict"
    # We do NOT collapse to majority vote
    if has_conflict:
        governance_label = "conflict"
        # Keep first vote's values but mark as conflicted
        truth_label = truth_values[0] if truth_values else None
        safety_label = safety_values[0] if safety_values else None
        utility_label = utility_values[0] if utility_values else None
    else:
        # Unanimous - use the shared value
        truth_label = truth_values[0] if truth_values else None
        safety_label = safety_values[0] if safety_values else None
        utility_label = utility_values[0] if utility_values else None
        governance_label = governance_values[0] if governance_values else "no_decision"
    
    return create_council_label(
        candidate_id=candidate_id,
        truth_label=truth_label,
        safety_label=safety_label,
        utility_label=utility_label,
        governance_label=governance_label,
        has_conflict=has_conflict,
        job_seed=job_seed
    )


# =============================================================================
# CANDIDATE COVERAGE CHECK
# =============================================================================

def check_candidate_coverage(candidate_ids: List[str]) -> Dict[str, Any]:
    """
    Check that all candidates have labels (100% coverage requirement).
    
    Returns:
        Dict with coverage stats and unlabeled candidates
    """
    conn = persistence.get_connection()
    try:
        labeled_ids = set()
        cur = persistence.execute_query(conn,
            "SELECT candidate_id FROM stage2_council_labels"
        )
        for row in persistence.fetch_all(cur):
            labeled_ids.add(row["candidate_id"])
        
        unlabeled = [cid for cid in candidate_ids if cid not in labeled_ids]
        
        return {
            "total_candidates": len(candidate_ids),
            "labeled_count": len(candidate_ids) - len(unlabeled),
            "unlabeled_count": len(unlabeled),
            "coverage_percent": (len(candidate_ids) - len(unlabeled)) / len(candidate_ids) * 100 if candidate_ids else 0,
            "unlabeled_candidates": unlabeled,
            "is_complete": len(unlabeled) == 0
        }
    finally:
        conn.close()
