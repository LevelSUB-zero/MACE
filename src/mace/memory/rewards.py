"""
Memory Rewards and Label Computation Module

Implements:
- Multi-dimensional labels (truth_status, utility_status, safety_status)
- Delayed reward computation
- Amendment tracking

Design decisions (from user spec):
- Truth validation: Hardcoded minimal known-facts dictionary (no external sources)
- Prematurity: unique_sources < 2 AND (current_tick - first_seen_tick) < 5
- Amendments: Dedicated append-only table (never infer from overwrites)
"""
import json
import datetime
from typing import Dict, List, Optional, Tuple

from mace.core import persistence, deterministic, canonical


# =============================================================================
# Known Facts Dictionary (Sparse, Adversarial)
# =============================================================================
# Only encode facts that are:
# - Uncontroversial
# - Structurally useful for testing failure modes
# Job: Generate negative examples, not answer questions

KNOWN_FACTS = {
    # World facts (capitals)
    "world/fact/geography/capital_australia": "canberra",
    "world/fact/geography/capital_france": "paris",
    "world/fact/geography/capital_japan": "tokyo",
    "world/fact/geography/capital_germany": "berlin",
    "world/fact/geography/capital_india": "new delhi",
    
    # Basic math/science
    "world/fact/math/ohms_law": "v=ir",
    "world/fact/math/pi_approx": "3.14159",
    "world/fact/science/water_formula": "h2o",
    "world/fact/science/speed_of_light": "299792458",
    
    # Common known-false claims (for testing rejection)
    # These are NOT in the dict, so any claim matching them is "incorrect"
}

# Known-false patterns (claims that should be marked incorrect)
KNOWN_FALSE_PATTERNS = [
    ("capital_australia", "sydney"),
    ("capital_france", "marseille"),
    ("capital_japan", "osaka"),
]


# =============================================================================
# Prematurity Configuration
# =============================================================================
# These are config values, not hardcoded (MEM-SNN will learn later)

PREMATURITY_CONFIG = {
    "min_unique_sources": 2,  # One source != memory-worthy
    "min_ticks_before_eligible": 5,  # <3 too aggressive, >10 delays learning
}


# =============================================================================
# Truth Status Computation
# =============================================================================

def compute_truth_status(proposed_key: str, value: str) -> str:
    """
    Compute truth_status for a candidate.
    
    Returns:
        - "correct": Matches known fact
        - "incorrect": Contradicts known fact
        - "uncertain": Not in knowledge base
    """
    value_lower = value.lower().strip()
    key_lower = proposed_key.lower().strip()
    
    # Check if key exists in known facts
    if key_lower in KNOWN_FACTS:
        known_value = KNOWN_FACTS[key_lower].lower()
        if value_lower == known_value:
            return "correct"
        else:
            return "incorrect"
    
    # Check against known-false patterns
    for pattern_key, false_value in KNOWN_FALSE_PATTERNS:
        if pattern_key in key_lower and false_value in value_lower:
            return "incorrect"
    
    # Not in knowledge base
    return "uncertain"


# =============================================================================
# Utility Status Computation
# =============================================================================

def compute_utility_status(
    proposed_key: str,
    value: str,
    unique_sources: int,
    first_seen_tick: int,
    current_tick: int,
    sem_state: Dict[str, str]
) -> str:
    """
    Compute utility_status for a candidate.
    
    Returns:
        - "useful": Novel, stable, and mature enough
        - "redundant": Already exists in SEM with same value
        - "premature": Not enough sources or ticks
    """
    # Check prematurity (Gate A: sources AND Gate B: ticks)
    if unique_sources < PREMATURITY_CONFIG["min_unique_sources"]:
        return "premature"
    
    ticks_elapsed = current_tick - first_seen_tick
    if ticks_elapsed < PREMATURITY_CONFIG["min_ticks_before_eligible"]:
        return "premature"
    
    # Check redundancy against SEM state
    if proposed_key in sem_state:
        existing_value = sem_state[proposed_key].lower().strip()
        if value.lower().strip() == existing_value:
            return "redundant"
    
    return "useful"


# =============================================================================
# Safety Status Computation
# =============================================================================

# Privacy patterns (simplified for Stage-2)
UNSAFE_PATTERNS = [
    "password", "credit_card", "ssn", "social_security",
    "bank_account", "api_key", "secret", "private_key",
]

def compute_safety_status(proposed_key: str, value: str) -> str:
    """
    Compute safety_status for a candidate.
    
    Returns:
        - "safe": No privacy/security concerns
        - "unsafe": Contains PII or sensitive data
    """
    combined = f"{proposed_key} {value}".lower()
    
    for pattern in UNSAFE_PATTERNS:
        if pattern in combined:
            return "unsafe"
    
    return "safe"


# =============================================================================
# Complete Multi-Dimensional Label
# =============================================================================

def compute_full_label(
    candidate: Dict,
    current_tick: int,
    sem_state: Dict[str, str],
    governance_decision: str,
    first_seen_tick: int = None
) -> Dict:
    """
    Compute complete multi-dimensional label for a candidate.
    
    Args:
        candidate: The candidate dict
        current_tick: Current simulation tick
        sem_state: Current semantic memory state
        governance_decision: Governance decision for this candidate
        first_seen_tick: Optional override for first_seen_tick (for sweeps)
    """
    proposed_key = candidate["proposed_key"]
    value = candidate["value"]
    
    # Extract source count from provenance
    provenance = candidate.get("provenance", [])
    unique_sources = len([p for p in provenance if p])  # Count non-empty
    
    # Estimate first_seen_tick if not provided
    # Use provenance size as proxy: more sources = seen earlier
    # Formula: With 3+ sources, assume seen at tick 0 (mature)
    if first_seen_tick is None:
        if unique_sources >= 3:
            first_seen_tick = 0  # Mature candidates escape prematurity
        elif unique_sources >= 2:
            first_seen_tick = max(0, current_tick - 6)  # Just past threshold
        else:
            first_seen_tick = max(0, current_tick - 2)  # Still premature
    
    return {
        "candidate_id": candidate["candidate_id"],
        "truth_status": compute_truth_status(proposed_key, value),
        "utility_status": compute_utility_status(
            proposed_key, value, unique_sources, 
            first_seen_tick, current_tick, sem_state
        ),
        "safety_status": compute_safety_status(proposed_key, value),
        "governance_decision": governance_decision,
    }


# =============================================================================
# Delayed Reward Computation
# =============================================================================

def compute_delayed_reward(
    candidate_id: str,
    baseline_metrics: Dict,
    post_metrics: Dict,
    has_amendments: bool
) -> float:
    """
    Compute delayed reward for a promoted candidate.
    
    Returns:
        +1.0: Improvement (retrieval_success + repair_loops decrease)
         0.0: Neutral
        -1.0: Regression or amendments occurred
    """
    # Amendments = definite negative (promotion was wrong)
    if has_amendments:
        return -1.0
    
    # Compare repair loops
    repair_before = baseline_metrics.get("repair_loops", 0)
    repair_after = post_metrics.get("repair_loops", 0)
    repair_delta = repair_before - repair_after  # Positive = improvement
    
    # Compare retrieval success
    retrieval_before = baseline_metrics.get("retrieval_success", 0)
    retrieval_after = post_metrics.get("retrieval_success", 0)
    retrieval_delta = retrieval_after - retrieval_before  # Positive = improvement
    
    # Decision logic
    if repair_delta > 0 and retrieval_delta >= 0:
        return +1.0  # Clear improvement
    elif repair_delta < 0 or retrieval_delta < 0:
        return -1.0  # Regression
    else:
        return 0.0  # Neutral


# =============================================================================
# Amendment Table Operations
# =============================================================================

def log_amendment(
    canonical_key: str,
    old_value: str,
    new_value: str,
    reason: str,
    trigger: str,
    source_evidence: List[str] = None,
    linked_action_request: str = None
) -> str:
    """
    Log an amendment to the append-only Amendment table.
    
    Args:
        canonical_key: The SEM key being amended
        old_value: Previous value
        new_value: New corrected value
        reason: Why the amendment happened
        trigger: What caused it (conflict_detection, user_correction, external_validation)
        source_evidence: List of evidence IDs
        linked_action_request: Related action request ID
    
    Returns:
        amendment_id
    """
    if source_evidence is None:
        source_evidence = []
    
    amendment_payload = f"{canonical_key}:{old_value}:{new_value}:{reason}"
    amendment_id = deterministic.deterministic_id("amendment", amendment_payload)
    
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    amendment = {
        "amendment_id": amendment_id,
        "canonical_key": canonical_key,
        "old_value": old_value,
        "new_value": new_value,
        "reason": reason,
        "trigger": trigger,
        "source_evidence": source_evidence,
        "linked_action_request": linked_action_request,
        "timestamp_seeded": timestamp,
    }
    
    conn = persistence.get_connection()
    try:
        persistence.execute_query(conn,
            """INSERT INTO amendments 
               (amendment_id, canonical_key, old_value, new_value, reason, 
                trigger, source_evidence_json, linked_action_request, timestamp_seeded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                amendment_id,
                canonical_key,
                old_value,
                new_value,
                reason,
                trigger,
                json.dumps(source_evidence),
                linked_action_request,
                timestamp
            )
        )
        conn.commit()
        return amendment_id
    finally:
        conn.close()


def get_amendments_for_key(canonical_key: str) -> List[Dict]:
    """Get all amendments for a specific key."""
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn,
            "SELECT * FROM amendments WHERE canonical_key = ? ORDER BY timestamp_seeded",
            (canonical_key,)
        )
        rows = persistence.fetch_all(cur)
        
        amendments = []
        for row in rows:
            amendments.append({
                "amendment_id": row["amendment_id"],
                "canonical_key": row["canonical_key"],
                "old_value": row["old_value"],
                "new_value": row["new_value"],
                "reason": row["reason"],
                "trigger": row["trigger"],
                "source_evidence": json.loads(row["source_evidence_json"]),
                "linked_action_request": row["linked_action_request"],
                "timestamp_seeded": row["timestamp_seeded"],
            })
        
        return amendments
    finally:
        conn.close()


def has_amendments_for_candidate(candidate_id: str, canonical_key: str) -> bool:
    """Check if a candidate's promoted value was later amended."""
    amendments = get_amendments_for_key(canonical_key)
    return len(amendments) > 0


def get_all_amendments() -> List[Dict]:
    """Get all amendments."""
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn,
            "SELECT * FROM amendments ORDER BY timestamp_seeded"
        )
        rows = persistence.fetch_all(cur)
        
        return [{
            "amendment_id": row["amendment_id"],
            "canonical_key": row["canonical_key"],
            "old_value": row["old_value"],
            "new_value": row["new_value"],
            "reason": row["reason"],
            "trigger": row["trigger"],
            "source_evidence": json.loads(row["source_evidence_json"]),
            "linked_action_request": row["linked_action_request"],
            "timestamp_seeded": row["timestamp_seeded"],
        } for row in rows]
    finally:
        conn.close()
