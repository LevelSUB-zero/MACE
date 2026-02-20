"""
Stage-2 Deterministic Candidate Generation (AUTHORITATIVE)

Purpose: Turn raw experience into explicit hypotheses.
Spec: docs/stage2_candidate_semantics.md

Core Doctrine:
- A candidate is NOT truth
- A candidate is NOT memory  
- A candidate is a question posed to governance

All candidates are:
- Deterministically ID'd
- Feature-locked (6 features only)
- Replay-stable
"""

import json
from typing import List, Dict, Any, Optional

from mace.core import deterministic, canonical, persistence
from mace.config import config_loader
from mace.stage2 import events


# =============================================================================
# FEATURE SET (LOCKED - DO NOT EXPAND)
# =============================================================================
# Spec: docs/stage2_candidate_semantics.md
# Each feature answers a specific epistemic question

CANDIDATE_FEATURES = [
    "frequency",           # "Is this recurring?"
    "consistency",         # "Is this stable?"
    "recency",             # "Is this current?"
    "source_diversity",    # "Is this echoed?"
    "semantic_novelty",    # "Is this new?"
    "governance_conflict_flag"  # "Is this allowed?"
]

# Schema version for candidates
CANDIDATE_SCHEMA_VERSION = "2.0"


def _validate_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize feature dict to exactly the 6 locked features.
    
    Raises ValueError if feature creep is detected.
    """
    # Check for feature creep
    for key in features.keys():
        if key not in CANDIDATE_FEATURES:
            raise ValueError(
                f"Feature creep detected: '{key}' is not in locked feature set. "
                f"This requires governance doc change."
            )
    
    # Ensure all features exist with defaults
    normalized = {
        "frequency": features.get("frequency", 0),
        "consistency": features.get("consistency", 0.0),
        "recency": features.get("recency", 0.0),
        "source_diversity": features.get("source_diversity", 0),
        "semantic_novelty": features.get("semantic_novelty", 1.0),
        "governance_conflict_flag": features.get("governance_conflict_flag", False)
    }
    
    return normalized


def generate_candidate_id(job_seed: str, episodic_ids: List[str], counter: int = 0) -> str:
    """
    Generate deterministic candidate ID.
    
    Formula: hash(seed + episodic_ids + counter)
    Same inputs → same candidate ID (reproducible)
    """
    if deterministic.get_seed() is None:
        deterministic.init_seed(job_seed)
    
    id_content = f"{job_seed}:{json.dumps(sorted(episodic_ids))}:{counter}"
    return deterministic.deterministic_id("stage2_candidate", id_content)


def create_candidate(
    proposed_key: str,
    value: str,
    features: Dict[str, Any],
    episodic_ids: List[str],
    job_seed: str,
    counter: int = 0
) -> Dict[str, Any]:
    """
    Create a Stage-2 candidate from episodic entries.
    
    Args:
        proposed_key: The canonical SEM key this candidate proposes
        value: The proposed value
        features: Feature dict (validated to 6 locked features)
        episodic_ids: List of episodic memory IDs this candidate derived from
        job_seed: Job seed for deterministic ID generation
        counter: Counter for disambiguation if same episodics produce multiple candidates
    
    Returns:
        Candidate dict with deterministic ID
    """
    # Validate features (raises on feature creep)
    validated_features = _validate_features(features)
    
    # Generate deterministic ID
    candidate_id = generate_candidate_id(job_seed, episodic_ids, counter)
    
    candidate = {
        "candidate_id": candidate_id,
        "proposed_key": proposed_key,
        "value": value,
        "features": validated_features,
        "episodic_ids": episodic_ids,
        "job_seed": job_seed,
        "schema_version": CANDIDATE_SCHEMA_VERSION
    }
    
    return candidate


def persist_candidate(candidate: Dict[str, Any]) -> str:
    """
    Persist a candidate to the Stage-2 candidate store.
    Also logs a candidate_create event.
    
    Returns candidate_id.
    """
    conn = persistence.get_connection()
    try:
        import datetime
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        persistence.execute_query(conn,
            """INSERT INTO stage2_candidates 
               (candidate_id, features_json, proposed_key, value, episodic_ids_json, job_seed, schema_version, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate["candidate_id"],
                canonical.canonical_json_serialize(candidate["features"]),
                candidate["proposed_key"],
                candidate["value"],
                canonical.canonical_json_serialize(candidate["episodic_ids"]),
                candidate["job_seed"],
                candidate["schema_version"],
                created_at
            )
        )
        conn.commit()
        
        # Log event
        events.log_candidate_create(
            candidate_id=candidate["candidate_id"],
            proposed_key=candidate["proposed_key"],
            features=candidate["features"],
            evidence_ids=candidate["episodic_ids"],
            job_seed=candidate["job_seed"]
        )
        
        return candidate["candidate_id"]
    finally:
        conn.close()


def get_candidate(candidate_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a candidate by ID."""
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn,
            "SELECT * FROM stage2_candidates WHERE candidate_id = ?",
            (candidate_id,)
        )
        row = persistence.fetch_one(cur)
        if row:
            return {
                "candidate_id": row["candidate_id"],
                "proposed_key": row["proposed_key"],
                "value": row["value"],
                "features": json.loads(row["features_json"]),
                "episodic_ids": json.loads(row["episodic_ids_json"]),
                "job_seed": row["job_seed"],
                "schema_version": row["schema_version"]
            }
        return None
    finally:
        conn.close()


def compute_features_from_episodes(
    episodes: List[Dict[str, Any]],
    existing_sem_keys: List[str] = None
) -> Dict[str, Any]:
    """
    Compute the 6 locked features from a list of episodic entries.
    
    This is a deterministic computation - same episodes → same features.
    """
    if not episodes:
        return _validate_features({})
    
    existing_sem_keys = existing_sem_keys or []
    
    # Frequency: count of episodes
    frequency = len(episodes)
    
    # Consistency: measure of value stability across episodes
    # (simplified: if all have same payload hash, consistency = 1.0)
    payloads = [canonical.canonical_json_serialize(ep.get("payload", {})) for ep in episodes]
    unique_payloads = set(payloads)
    consistency = 1.0 / len(unique_payloads) if unique_payloads else 0.0
    
    # Recency: based on most recent episode timestamp
    # (simplified: fraction of episodes from "recent" period)
    recency = min(1.0, frequency / 10.0)  # Caps at 1.0 after 10 episodes
    
    # Source Diversity: count of unique sources
    sources = set()
    for ep in episodes:
        source = ep.get("payload", {}).get("source", ep.get("group", "unknown"))
        sources.add(source)
    source_diversity = len(sources)
    
    # Semantic Novelty: inverse similarity to existing SEM keys
    # (simplified: 1.0 if no matches, 0.0 if exact key exists)
    proposed_key = episodes[0].get("payload", {}).get("proposed_key", "")
    semantic_novelty = 0.0 if proposed_key in existing_sem_keys else 1.0
    
    # Governance Conflict Flag: check for policy violations
    governance_conflict_flag = False
    for ep in episodes:
        if ep.get("payload", {}).get("governance_conflict", False):
            governance_conflict_flag = True
            break
    
    return _validate_features({
        "frequency": frequency,
        "consistency": consistency,
        "recency": recency,
        "source_diversity": source_diversity,
        "semantic_novelty": semantic_novelty,
        "governance_conflict_flag": governance_conflict_flag
    })
