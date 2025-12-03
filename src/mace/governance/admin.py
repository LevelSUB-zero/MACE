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
