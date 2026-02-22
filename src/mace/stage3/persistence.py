"""
Durable Persistence Layer - Stage-3 Production Hardening

P0 Item 1: ReflectiveLog must survive process restart.
P0 Item 2: Guard state must persist across restarts.

Uses SQLite for portability. Production can swap to PostgreSQL.

Schema versioning baked into every row.
Append-only with idempotent inserts (UPSERT on event_id).
Write-ahead logging enabled.
"""

import os
import json
import sqlite3
import hashlib
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "stage3.db")
SCHEMA_VERSION = "3.0"


@contextmanager
def get_connection(db_path: str = None):
    """Get SQLite connection with WAL mode enabled."""
    path = db_path or os.environ.get("STAGE3_DB_PATH", DEFAULT_DB_PATH)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")  # Write-ahead logging
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database(db_path: str = None):
    """Initialize database schema."""
    with get_connection(db_path) as conn:
        # ReflectiveLog - append-only advisory and observation log
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reflective_log (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                schema_version TEXT NOT NULL DEFAULT '3.0',
                job_seed TEXT NOT NULL,
                decision_hash TEXT,
                advisory_id TEXT,
                observation_id TEXT,
                payload TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                immutable_signature TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reflective_job_seed ON reflective_log(job_seed)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reflective_decision_hash ON reflective_log(decision_hash)")
        
        # Guard State - persisted kill-switch and mode
        conn.execute("""
            CREATE TABLE IF NOT EXISTS guard_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Violations Ledger - all violations ever recorded
        conn.execute("""
            CREATE TABLE IF NOT EXISTS violations_ledger (
                violation_id TEXT PRIMARY KEY,
                violation_type TEXT NOT NULL,
                job_seed TEXT,
                description TEXT,
                evidence TEXT,
                severity TEXT NOT NULL DEFAULT 'critical',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_violations_type ON violations_ledger(violation_type)")
        
        # Advisory Outputs - indexed for replay verification
        conn.execute("""
            CREATE TABLE IF NOT EXISTS advisory_outputs (
                advisory_id TEXT PRIMARY KEY,
                job_seed TEXT NOT NULL,
                source_model TEXT NOT NULL,
                generator_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                scoring_method TEXT NOT NULL,
                calibration_version TEXT NOT NULL,
                scope TEXT NOT NULL,
                advice_type TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence_estimate TEXT NOT NULL,
                canonical_json TEXT NOT NULL,
                immutable_signature TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_advisory_job_seed ON advisory_outputs(job_seed)")
        
        # Meta Observations - divergence tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meta_observations (
                observation_id TEXT PRIMARY KEY,
                job_seed TEXT NOT NULL,
                advisory_id TEXT,
                divergence_type TEXT NOT NULL,
                divergence_description TEXT,
                impact_estimate TEXT NOT NULL,
                actual_outcome TEXT,
                canonical_json TEXT NOT NULL,
                immutable_signature TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_observations_job_seed ON meta_observations(job_seed)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_observations_advisory ON meta_observations(advisory_id)")


# =============================================================================
# REFLECTIVE LOG PERSISTENCE
# =============================================================================

def persist_to_reflective_log(
    event_type: str,
    job_seed: str,
    payload: Dict[str, Any],
    decision_hash: str = None,
    advisory_id: str = None,
    observation_id: str = None,
    db_path: str = None
) -> str:
    """
    Persist event to ReflectiveLog with idempotent insert.
    
    Returns event_id.
    """
    # Generate deterministic event_id
    content_hash = hashlib.sha256(
        f"{job_seed}:{event_type}:{json.dumps(payload, sort_keys=True)}".encode()
    ).hexdigest()[:32]
    event_id = f"evt_{content_hash}"
    
    # Compute signature
    signature = hashlib.sha256(
        f"{event_id}:{SCHEMA_VERSION}:{json.dumps(payload, sort_keys=True)}".encode()
    ).hexdigest()[:32]
    
    with get_connection(db_path) as conn:
        # UPSERT - idempotent insert
        conn.execute("""
            INSERT INTO reflective_log 
            (event_id, event_type, schema_version, job_seed, decision_hash, 
             advisory_id, observation_id, payload, immutable_signature, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO NOTHING
        """, (
            event_id, event_type, SCHEMA_VERSION, job_seed, decision_hash,
            advisory_id, observation_id, json.dumps(payload), signature,
            datetime.utcnow().isoformat()
        ))
    
    return event_id


def get_reflective_log_entries(
    job_seed: str = None,
    event_type: str = None,
    limit: int = 100,
    db_path: str = None
) -> List[Dict[str, Any]]:
    """Query reflective log entries."""
    with get_connection(db_path) as conn:
        query = "SELECT * FROM reflective_log WHERE 1=1"
        params = []
        
        if job_seed:
            query += " AND job_seed = ?"
            params.append(job_seed)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# GUARD STATE PERSISTENCE
# =============================================================================

def set_guard_state(key: str, value: str, db_path: str = None):
    """Set a guard state value (persisted)."""
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO guard_state (state_key, state_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(state_key) DO UPDATE SET 
                state_value = excluded.state_value,
                updated_at = excluded.updated_at
        """, (key, value, datetime.utcnow().isoformat()))


def get_guard_state(key: str, db_path: str = None) -> Optional[str]:
    """Get a guard state value."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT state_value FROM guard_state WHERE state_key = ?", (key,)
        )
        row = cursor.fetchone()
        return row["state_value"] if row else None


def is_killswitch_active(db_path: str = None) -> bool:
    """Check if kill-switch is active (persisted state)."""
    value = get_guard_state("killswitch_active", db_path)
    return value == "true"


def activate_killswitch(job_seed: str, reason: str, db_path: str = None):
    """Activate kill-switch (one-way, persisted)."""
    set_guard_state("killswitch_active", "true", db_path)
    set_guard_state("killswitch_reason", reason, db_path)
    set_guard_state("killswitch_job_seed", job_seed, db_path)
    set_guard_state("killswitch_activated_at", datetime.utcnow().isoformat(), db_path)


def get_current_learning_mode(db_path: str = None) -> str:
    """Get current learning mode (persisted)."""
    return get_guard_state("learning_mode", db_path) or "shadow"


def set_learning_mode(mode: str, db_path: str = None):
    """Set learning mode (persisted)."""
    if mode not in ("shadow", "advisory"):
        raise ValueError(f"Invalid mode: {mode}")
    set_guard_state("learning_mode", mode, db_path)


# =============================================================================
# VIOLATIONS LEDGER
# =============================================================================

def record_violation(
    violation_id: str,
    violation_type: str,
    job_seed: str,
    description: str,
    evidence: Dict[str, Any] = None,
    severity: str = "critical",
    db_path: str = None
):
    """Record a violation to the ledger (never deleted)."""
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO violations_ledger 
            (violation_id, violation_type, job_seed, description, evidence, severity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(violation_id) DO NOTHING
        """, (
            violation_id, violation_type, job_seed, description,
            json.dumps(evidence) if evidence else None, severity,
            datetime.utcnow().isoformat()
        ))


def get_violations(
    violation_type: str = None,
    limit: int = 100,
    db_path: str = None
) -> List[Dict[str, Any]]:
    """Get violations from ledger."""
    with get_connection(db_path) as conn:
        if violation_type:
            cursor = conn.execute(
                "SELECT * FROM violations_ledger WHERE violation_type = ? ORDER BY created_at DESC LIMIT ?",
                (violation_type, limit)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM violations_ledger ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        return [dict(row) for row in cursor.fetchall()]


def count_violations(db_path: str = None) -> int:
    """Count total violations."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM violations_ledger")
        return cursor.fetchone()[0]


# =============================================================================
# ADVISORY OUTPUT PERSISTENCE (WITH VERSIONING)
# =============================================================================

@dataclass
class AdvisoryVersion:
    """Advisory versioning metadata - P0 Item 3."""
    generator_id: str        # "mem-snn-shadow-v1"
    model_version: str       # "2026-01-24-a"
    scoring_method: str      # "shadow" | "real" | "fallback"
    calibration_version: str # "v1.0"


def persist_advisory_output(
    advisory_id: str,
    job_seed: str,
    source_model: str,
    version: AdvisoryVersion,
    scope: str,
    advice_type: str,
    content: str,
    confidence_estimate: str,
    canonical_json: str,
    signature: str,
    db_path: str = None
):
    """Persist advisory output with full versioning."""
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO advisory_outputs 
            (advisory_id, job_seed, source_model, generator_id, model_version,
             scoring_method, calibration_version, scope, advice_type, content,
             confidence_estimate, canonical_json, immutable_signature, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(advisory_id) DO NOTHING
        """, (
            advisory_id, job_seed, source_model, version.generator_id,
            version.model_version, version.scoring_method, version.calibration_version,
            scope, advice_type, content, confidence_estimate, canonical_json, signature,
            datetime.utcnow().isoformat()
        ))


def get_advisory_by_id(advisory_id: str, db_path: str = None) -> Optional[Dict[str, Any]]:
    """Get advisory by ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM advisory_outputs WHERE advisory_id = ?", (advisory_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def verify_advisory_replay(
    advisory_id: str,
    expected_canonical_json: str,
    db_path: str = None
) -> bool:
    """
    Verify advisory replay fidelity - P0 Item 4.
    
    Returns True if stored canonical_json matches expected.
    """
    stored = get_advisory_by_id(advisory_id, db_path)
    if not stored:
        return False
    return stored["canonical_json"] == expected_canonical_json


# =============================================================================
# META OBSERVATION PERSISTENCE
# =============================================================================

def persist_meta_observation(
    observation_id: str,
    job_seed: str,
    advisory_id: str,
    divergence_type: str,
    divergence_description: str,
    impact_estimate: str,
    actual_outcome: str,
    canonical_json: str,
    signature: str,
    db_path: str = None
):
    """Persist meta-observation."""
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO meta_observations 
            (observation_id, job_seed, advisory_id, divergence_type, 
             divergence_description, impact_estimate, actual_outcome,
             canonical_json, immutable_signature, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(observation_id) DO NOTHING
        """, (
            observation_id, job_seed, advisory_id, divergence_type,
            divergence_description, impact_estimate, actual_outcome,
            canonical_json, signature, datetime.utcnow().isoformat()
        ))


def get_divergence_stats(db_path: str = None) -> Dict[str, int]:
    """Get divergence statistics."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("""
            SELECT divergence_type, COUNT(*) as count 
            FROM meta_observations 
            GROUP BY divergence_type
        """)
        return {row["divergence_type"]: row["count"] for row in cursor.fetchall()}


# =============================================================================
# REPLAY VERIFICATION - P0 Item 4
# =============================================================================

def log_replay_divergence(
    job_seed: str,
    original_signature: str,
    replay_signature: str,
    divergence_details: str,
    db_path: str = None
):
    """Log when replay produces different output (quarantine)."""
    persist_to_reflective_log(
        event_type="REPLAY_DIVERGENCE",
        job_seed=job_seed,
        payload={
            "original_signature": original_signature,
            "replay_signature": replay_signature,
            "divergence_details": divergence_details,
            "quarantine": True,
        },
        db_path=db_path
    )


def verify_replay_fidelity(
    job_seed: str,
    original_entries: List[Dict[str, Any]],
    replay_entries: List[Dict[str, Any]],
    db_path: str = None
) -> bool:
    """
    Verify replay produces identical output.
    
    If divergence, logs to REPLAY_DIVERGENCE and returns False.
    """
    if len(original_entries) != len(replay_entries):
        log_replay_divergence(
            job_seed=job_seed,
            original_signature=f"count:{len(original_entries)}",
            replay_signature=f"count:{len(replay_entries)}",
            divergence_details="Entry count mismatch",
            db_path=db_path
        )
        return False
    
    for orig, replay in zip(original_entries, replay_entries):
        if orig.get("immutable_signature") != replay.get("immutable_signature"):
            log_replay_divergence(
                job_seed=job_seed,
                original_signature=orig.get("immutable_signature", ""),
                replay_signature=replay.get("immutable_signature", ""),
                divergence_details="Signature mismatch",
                db_path=db_path
            )
            return False
    
    return True
