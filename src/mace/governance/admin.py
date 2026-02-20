import secrets
import datetime
import json
from mace.core import persistence, deterministic, canonical

def generate_token(purpose, ttl_hours=24, admin_id="system"):
    """
    Generate an admin token with expiration.
    Returns token string and token_id.
    """
    # Generate secure random token
    token = secrets.token_urlsafe(32)
    
    # Create deterministic token ID
    token_id = deterministic.deterministic_id("admin_token", f"{token}{purpose}{admin_id}")
    
    created_at = datetime.datetime.now(datetime.timezone.utc)
    expires_at = created_at + datetime.timedelta(hours=ttl_hours)
    
    conn = persistence.get_connection()
    try:
        persistence.execute_query(conn,
            "INSERT INTO admin_tokens (token_id, token_hash, purpose, created_by, created_at, expires_at, revoked) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (token_id, token, purpose, admin_id, created_at.isoformat(), expires_at.isoformat(), False)
        )
        conn.commit()
        return token, token_id
    finally:
        conn.close()

def verify_token(token):
    """
    Verify token is valid and not expired/revoked.
    Returns dict with {valid: bool, purpose: str, token_id: str} or {valid: False, reason: str}
    """
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn, "SELECT * FROM admin_tokens WHERE token_hash = ?", (token,))
        row = persistence.fetch_one(cur)
        
        if not row:
            return {"valid": False, "reason": "TOKEN_NOT_FOUND"}
            
        if row["revoked"]:
            return {"valid": False, "reason": "TOKEN_REVOKED"}
            
        expires_at = datetime.datetime.fromisoformat(row["expires_at"])
        if datetime.datetime.now(datetime.timezone.utc) > expires_at:
            return {"valid": False, "reason": "TOKEN_EXPIRED"}
            
        return {
            "valid": True,
            "purpose": row["purpose"],
            "token_id": row["token_id"],
            "created_by": row["created_by"]
        }
    finally:
        conn.close()

def revoke_token(token_id):
    """
    Revoke a token by ID.
    """
    conn = persistence.get_connection()
    try:
        persistence.execute_query(conn, "UPDATE admin_tokens SET revoked = ? WHERE token_id = ?", (True, token_id))
        conn.commit()
        return True
    finally:
        conn.close()


# =============================================================================
# Governance Decision Logging (LR-01)
# =============================================================================

def log_governance_decision(candidate_id: str, decision: str, reason: str, 
                            heuristic_would_approve: bool = None, admin_id: str = "system") -> str:
    """
    Log a governance decision for a MEMCandidate.
    
    Args:
        candidate_id: The MEMCandidate ID
        decision: 'approve' or 'reject'
        reason: Explanation for the decision
        heuristic_would_approve: What the heuristic would have decided (for comparison)
        admin_id: Who made the decision
    
    Returns:
        decision_id
    """
    decision_id = deterministic.deterministic_id("gov_decision", f"{candidate_id}:{decision}:{admin_id}")
    decided_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    conn = persistence.get_connection()
    try:
        persistence.execute_query(conn,
            """INSERT OR REPLACE INTO governance_decisions 
               (decision_id, candidate_id, decision, reason, heuristic_would_approve, decided_by, decided_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                decision_id,
                candidate_id,
                decision,
                reason,
                1 if heuristic_would_approve else 0 if heuristic_would_approve is not None else None,
                admin_id,
                decided_at
            )
        )
        conn.commit()
        return decision_id
    finally:
        conn.close()


def get_governance_decisions() -> list:
    """
    Retrieve all governance decisions.
    """
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn, 
            "SELECT * FROM governance_decisions ORDER BY decided_at")
        rows = persistence.fetch_all(cur)
        
        decisions = []
        for row in rows:
            decisions.append({
                "decision_id": row["decision_id"],
                "candidate_id": row["candidate_id"],
                "decision": row["decision"],
                "reason": row["reason"],
                "heuristic_would_approve": bool(row["heuristic_would_approve"]) if row["heuristic_would_approve"] is not None else None,
                "decided_by": row["decided_by"],
                "decided_at": row["decided_at"]
            })
        
        return decisions
    finally:
        conn.close()


def get_decision_for_candidate(candidate_id: str) -> dict:
    """
    Get the governance decision for a specific candidate.
    """
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn,
            "SELECT * FROM governance_decisions WHERE candidate_id = ?", (candidate_id,))
        row = persistence.fetch_one(cur)
        
        if row:
            return {
                "decision_id": row["decision_id"],
                "candidate_id": row["candidate_id"],
                "decision": row["decision"],
                "reason": row["reason"],
                "heuristic_would_approve": bool(row["heuristic_would_approve"]) if row["heuristic_would_approve"] is not None else None,
                "decided_by": row["decided_by"],
                "decided_at": row["decided_at"]
            }
        return None
    finally:
        conn.close()


def log_outcome_measurement(candidate_id: str, query: str, phase: str, metrics: dict) -> str:
    """
    Log outcome measurement for a candidate.
    
    Args:
        candidate_id: The MEMCandidate ID
        query: The test query used
        phase: 'baseline' or 'post_promotion'
        metrics: Dict with repair_loops, fallback_count, confidence, latency_class
    
    Returns:
        outcome_id
    """
    outcome_id = deterministic.deterministic_id("outcome", f"{candidate_id}:{query}:{phase}")
    measured_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    conn = persistence.get_connection()
    try:
        persistence.execute_query(conn,
            """INSERT OR REPLACE INTO outcome_measurements 
               (outcome_id, candidate_id, query, phase, metrics_json, measured_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                outcome_id,
                candidate_id,
                query,
                phase,
                json.dumps(metrics),
                measured_at
            )
        )
        conn.commit()
        return outcome_id
    finally:
        conn.close()


def get_outcome_measurements(candidate_id: str = None) -> list:
    """
    Retrieve outcome measurements.
    """
    conn = persistence.get_connection()
    try:
        if candidate_id:
            cur = persistence.execute_query(conn,
                "SELECT * FROM outcome_measurements WHERE candidate_id = ? ORDER BY measured_at",
                (candidate_id,))
        else:
            cur = persistence.execute_query(conn,
                "SELECT * FROM outcome_measurements ORDER BY measured_at")
        
        rows = persistence.fetch_all(cur)
        
        outcomes = []
        for row in rows:
            outcomes.append({
                "outcome_id": row["outcome_id"],
                "candidate_id": row["candidate_id"],
                "query": row["query"],
                "phase": row["phase"],
                "metrics": json.loads(row["metrics_json"]),
                "measured_at": row["measured_at"]
            })
        
        return outcomes
    finally:
        conn.close()
