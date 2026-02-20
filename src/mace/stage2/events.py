"""
Stage-2 Memory Event Instrumentation (AUTHORITATIVE)

Purpose: Learning quality is bounded by observability quality.
Spec: docs/stage2_ideology.md

Rule: If it affects future learning, it must be logged.

All events are:
- Append-only
- Deterministically ID'd
- HMAC signed
- Replayable
"""

import json
import datetime
from typing import List, Optional, Dict, Any

from mace.core import deterministic, canonical, signing, persistence


# =============================================================================
# EVENT TYPES (FROZEN - DO NOT EXPAND)
# =============================================================================
# Spec: Phase 2.1 of execution plan

EVENT_TYPES = [
    "wm_insert",
    "wm_expire",
    "episodic_write",
    "candidate_create",
    "council_vote",
    "amendment"
]

# Schema version for event format
EVENT_SCHEMA_VERSION = "2.0"


# =============================================================================
# EVENT SCHEMA (CANONICAL - FROZEN)
# =============================================================================

def _create_event(
    event_type: str,
    source_module: str,
    evidence_ids: List[str],
    payload: Dict[str, Any],
    job_seed: Optional[str] = None,
    trace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a canonical event object.
    
    Args:
        event_type: One of EVENT_TYPES (validated)
        source_module: Name of the module that generated this event
        evidence_ids: List of related evidence/episodic IDs
        payload: Event-specific payload data
        job_seed: Optional job seed for deterministic ID generation
        trace_id: Optional trace ID for request correlation
    
    Returns:
        Canonical event dict
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {event_type}. Must be one of {EVENT_TYPES}")
    
    # Use deterministic ID generation
    seed = job_seed or deterministic.get_seed() or "event_fallback"
    if deterministic.get_seed() is None:
        deterministic.init_seed(seed)
    
    # Create deterministic event ID
    id_content = f"{event_type}:{source_module}:{json.dumps(evidence_ids, sort_keys=True)}"
    event_id = deterministic.deterministic_id("stage2_event", id_content)
    
    # Deterministic timestamp
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    event = {
        "event_id": event_id,
        "event_type": event_type,
        "job_seed": seed,
        "trace_id": trace_id or deterministic.deterministic_id("trace", timestamp),
        "source_module": source_module,
        "evidence_ids": evidence_ids,
        "timestamp_seeded": timestamp,
        "schema_version": EVENT_SCHEMA_VERSION,
        "payload": payload
    }
    
    return event


def _sign_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Sign an event with HMAC for tamper detection."""
    # Create immutable subpayload for signing
    subpayload = {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "evidence_ids": event["evidence_ids"],
        "schema_version": event["schema_version"]
    }
    
    key_id = "stage2_event_key"
    signature = signing.sign_payload(subpayload, key_id)
    
    event["signature"] = signature
    event["signature_key_id"] = key_id
    
    return event


def _persist_event(event: Dict[str, Any]) -> str:
    """
    Persist event to append-only log.
    Returns event_id.
    """
    conn = persistence.get_connection()
    try:
        event_json = canonical.canonical_json_serialize(event)
        
        persistence.execute_query(conn,
            """INSERT INTO stage2_events 
               (event_id, event_type, source_module, event_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (event["event_id"], event["event_type"], event["source_module"],
             event_json, event["timestamp_seeded"])
        )
        conn.commit()
        return event["event_id"]
    finally:
        conn.close()


# =============================================================================
# PUBLIC API: Event Logging Functions
# =============================================================================

def log_wm_insert(
    item_id: str,
    content_summary: str,
    source_module: str = "wm",
    evidence_ids: List[str] = None,
    job_seed: str = None
) -> str:
    """Log a Working Memory insert event."""
    event = _create_event(
        event_type="wm_insert",
        source_module=source_module,
        evidence_ids=evidence_ids or [],
        payload={
            "item_id": item_id,
            "content_summary": content_summary
        },
        job_seed=job_seed
    )
    event = _sign_event(event)
    return _persist_event(event)


def log_wm_expire(
    item_id: str,
    reason: str,
    source_module: str = "wm",
    evidence_ids: List[str] = None,
    job_seed: str = None
) -> str:
    """Log a Working Memory expire event."""
    event = _create_event(
        event_type="wm_expire",
        source_module=source_module,
        evidence_ids=evidence_ids or [],
        payload={
            "item_id": item_id,
            "reason": reason
        },
        job_seed=job_seed
    )
    event = _sign_event(event)
    return _persist_event(event)


def log_episodic_write(
    episodic_id: str,
    summary: str,
    source_module: str = "episodic",
    evidence_ids: List[str] = None,
    job_seed: str = None
) -> str:
    """Log an Episodic Memory write event."""
    event = _create_event(
        event_type="episodic_write",
        source_module=source_module,
        evidence_ids=evidence_ids or [episodic_id],
        payload={
            "episodic_id": episodic_id,
            "summary": summary
        },
        job_seed=job_seed
    )
    event = _sign_event(event)
    return _persist_event(event)


def log_candidate_create(
    candidate_id: str,
    proposed_key: str,
    features: Dict[str, Any],
    source_module: str = "consolidator",
    evidence_ids: List[str] = None,
    job_seed: str = None
) -> str:
    """Log a Candidate creation event."""
    event = _create_event(
        event_type="candidate_create",
        source_module=source_module,
        evidence_ids=evidence_ids or [],
        payload={
            "candidate_id": candidate_id,
            "proposed_key": proposed_key,
            "features": features
        },
        job_seed=job_seed
    )
    event = _sign_event(event)
    return _persist_event(event)


def log_council_vote(
    vote_id: str,
    candidate_id: str,
    labels: Dict[str, Any],
    source_module: str = "council",
    evidence_ids: List[str] = None,
    job_seed: str = None
) -> str:
    """Log a Council vote/decision event."""
    event = _create_event(
        event_type="council_vote",
        source_module=source_module,
        evidence_ids=evidence_ids or [candidate_id],
        payload={
            "vote_id": vote_id,
            "candidate_id": candidate_id,
            "labels": labels
        },
        job_seed=job_seed
    )
    event = _sign_event(event)
    return _persist_event(event)


def log_amendment(
    amendment_id: str,
    original_candidate_id: str,
    delay_ticks: int,
    reward: int,
    reason: str,
    source_module: str = "amendments",
    evidence_ids: List[str] = None,
    job_seed: str = None
) -> str:
    """Log an Amendment event (delayed reward)."""
    event = _create_event(
        event_type="amendment",
        source_module=source_module,
        evidence_ids=evidence_ids or [original_candidate_id],
        payload={
            "amendment_id": amendment_id,
            "original_candidate_id": original_candidate_id,
            "delay_ticks": delay_ticks,
            "reward": reward,
            "reason": reason
        },
        job_seed=job_seed
    )
    event = _sign_event(event)
    return _persist_event(event)


# =============================================================================
# EVENT RETRIEVAL (For Replay/Verification)
# =============================================================================

def get_events_by_type(event_type: str) -> List[Dict[str, Any]]:
    """Get all events of a specific type."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {event_type}")
    
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn,
            "SELECT event_json FROM stage2_events WHERE event_type = ? ORDER BY created_at",
            (event_type,)
        )
        rows = persistence.fetch_all(cur)
        return [json.loads(row["event_json"]) for row in rows]
    finally:
        conn.close()


def get_all_events() -> List[Dict[str, Any]]:
    """Get all Stage-2 events (for replay verification)."""
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn,
            "SELECT event_json FROM stage2_events ORDER BY created_at"
        )
        rows = persistence.fetch_all(cur)
        return [json.loads(row["event_json"]) for row in rows]
    finally:
        conn.close()


def verify_event_signature(event: Dict[str, Any]) -> bool:
    """Verify an event's HMAC signature."""
    subpayload = {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "evidence_ids": event["evidence_ids"],
        "schema_version": event["schema_version"]
    }
    
    key_id = event.get("signature_key_id", "stage2_event_key")
    expected_signature = signing.sign_payload(subpayload, key_id)
    
    return event.get("signature") == expected_signature
