"""
Module: advisory_events
Stage: 3
Purpose: Append-only, HMAC-signed event log for the Advisory System.
         All reflections, insights, flags, and council decisions are
         recorded here as deterministically ID'd events.

Part of MACE (Meta Aware Cognitive Engine).
Spec: docs/phase3/advisory_system_spec.md § 3.1, 3.3.8
"""

import json
from typing import List, Dict, Any, Optional

from mace.core import deterministic, canonical, signing, persistence

# =============================================================================
# EVENT TYPES (FROZEN - DO NOT EXPAND)
# =============================================================================

EVENT_TYPES = [
    "ADVICE_GENERATED",
    "ADVICE_INGESTED",
    "ADVICE_QUALITY_REPORT",
    "MISLEADING_ADVICE_FLAG",
    "PREMATURE_ADVICE_FLAG",
    "SAFETY_ADVICE_FLAG",
    "COUNCIL_EVALUATION",
    "DISAGREEMENT_LOG",
    "MODULE_POLICY_VIOLATION",
    "SILENT_INFLUENCE_ALERT",
    "ADVICE_USAGE_FORBIDDEN",
    "CONSTITUTION_VIOLATION",
    "SYSTEM_FREEZE",
    "STAGE3_ABORT",
    "MEM_ERROR",
    "MEM_MALFORMED",
    "MEM_INCONSISTENT",
    "MEM_NO_EVIDENCE",
    "REFLECTIVE_VIOLATION",
    "REPLAY_RESULT",
    "REPLAY_DIVERGENCE"
]

EVENT_SCHEMA_VERSION = "3.0"

# =============================================================================
# INTERNAL SCHEMA CREATION
# =============================================================================

def _create_event(
    event_type: str,
    source_module: str,
    payload: Dict[str, Any],
    evidence_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Create a canonical Stage 3 advisory event."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {event_type}. Must be one of {EVENT_TYPES}")
        
    evidence_ids = evidence_ids or []
    
    # We must use the seeded deterministic clock/sequence
    # We do NOT use datetime.now() anywhere in Stage 3 internals
    seed = deterministic.get_seed() or "advisory_fallback"
    if deterministic.get_seed() is None:
        deterministic.init_seed(seed)
        
    id_content = f"{event_type}:{source_module}:{json.dumps(evidence_ids, sort_keys=True)}"
    event_id = deterministic.deterministic_id("stage3_event", id_content)

    # Deterministic timestamp — no datetime.now() per convention.
    timestamp_seeded = deterministic.deterministic_id("stage3_tick", event_id)
    
    event = {
        "event_id": event_id,
        "event_type": event_type,
        "job_seed": seed,
        "source_module": source_module,
        "evidence_ids": evidence_ids,
        "timestamp_seeded": timestamp_seeded,
        "schema_version": EVENT_SCHEMA_VERSION,
        "payload": payload
    }
    return event

def _sign_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Sign an event with HMAC for tamper detection."""
    subpayload = {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "evidence_ids": event["evidence_ids"],
        "schema_version": event["schema_version"]
    }
    
    key_id = "stage3_advisory_key"
    signature = signing.sign_payload(subpayload, key_id)
    
    event["signature"] = signature
    event["signature_key_id"] = key_id
    return event

def _persist_event(event: Dict[str, Any]) -> str:
    """Persist event to append-only stage3_advice_events log."""
    conn = persistence.get_connection()
    try:
        event_json = canonical.canonical_json_serialize(event)
        persistence.execute_query(conn,
            """INSERT OR REPLACE INTO stage3_advice_events 
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
# PUBLIC EXPORTS
# =============================================================================

def get_events_by_type(event_type: str) -> List[Dict[str, Any]]:
    """Get all events of a specific type from Stage 3 log."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {event_type}")
    
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn,
            "SELECT event_json FROM stage3_advice_events WHERE event_type = ? ORDER BY created_at",
            (event_type,)
        )
        rows = persistence.fetch_all(cur)
        return [json.loads(row["event_json"]) for row in rows]
    finally:
        conn.close()

def append_advisory_event(
    event_type: str,
    source_module: str,
    payload: Dict[str, Any],
    evidence_ids: Optional[List[str]] = None
) -> str:
    """
    Append a new HMAC-signed advisory event to the log.
    
    Returns:
        The generated event_id.
    """
    event = _create_event(event_type, source_module, payload, evidence_ids)
    event = _sign_event(event)
    return _persist_event(event)
