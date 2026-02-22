"""
Kill-Switch Externalization - P1 Governance Hardening

P1 Item 12: Kill-switch must be:
- External to MACE process
- Monitored by watchdog
- One-way activation (hard to turn back on)
- Multi-party auth for reset

This module provides the interface and watchdog protocol.
"""

import os
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

# Import persistence for durable state
from mace.stage3.persistence import (
    set_guard_state, get_guard_state,
    is_killswitch_active, activate_killswitch as persist_killswitch,
    record_violation
)


# =============================================================================
# EXTERNAL KILL-SWITCH CONFIGURATION
# =============================================================================

# Default paths
DEFAULT_KILLSWITCH_FILE = Path.home() / ".mace" / "killswitch.flag"
DEFAULT_HEARTBEAT_FILE = Path.home() / ".mace" / "heartbeat.json"
DEFAULT_RESET_REQUESTS = Path.home() / ".mace" / "reset_requests"

# Heartbeat interval (seconds)
HEARTBEAT_INTERVAL = 30

# Required signatures for reset
REQUIRED_RESET_SIGNATURES = 2


@dataclass
class KillSwitchState:
    """External kill-switch state."""
    active: bool = False
    activated_at: Optional[str] = None
    activated_by: Optional[str] = None
    reason: Optional[str] = None
    job_seed: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "active": self.active,
            "activated_at": self.activated_at,
            "activated_by": self.activated_by,
            "reason": self.reason,
            "job_seed": self.job_seed,
        }


@dataclass
class Heartbeat:
    """Watchdog heartbeat."""
    timestamp: str
    process_id: int
    stage3_mode: str
    healthy: bool
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "process_id": self.process_id,
            "stage3_mode": self.stage3_mode,
            "healthy": self.healthy,
        }


@dataclass
class ResetRequest:
    """Multi-party reset request."""
    request_id: str
    requested_at: str
    requested_by: str
    reason: str
    signatures: List[str] = field(default_factory=list)
    approved: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "requested_at": self.requested_at,
            "requested_by": self.requested_by,
            "reason": self.reason,
            "signatures": self.signatures,
            "approved": self.approved,
        }


# =============================================================================
# EXTERNAL KILL-SWITCH OPERATIONS
# =============================================================================

class ExternalKillSwitch:
    """
    External kill-switch with file-based activation.
    
    Activation is one-way: creates a flag file that watchdog monitors.
    Reset requires multi-party authorization.
    """
    
    def __init__(
        self,
        killswitch_path: Path = None,
        heartbeat_path: Path = None,
        reset_path: Path = None,
        db_path: str = None
    ):
        self.killswitch_path = killswitch_path or DEFAULT_KILLSWITCH_FILE
        self.heartbeat_path = heartbeat_path or DEFAULT_HEARTBEAT_FILE
        self.reset_path = reset_path or DEFAULT_RESET_REQUESTS
        self.db_path = db_path
        
        # Ensure directories exist
        self.killswitch_path.parent.mkdir(parents=True, exist_ok=True)
        self.reset_path.mkdir(parents=True, exist_ok=True)
    
    def is_active(self) -> bool:
        """Check if kill-switch is active (file exists OR db flag set)."""
        # Check file first (external watchdog may have created it)
        if self.killswitch_path.exists():
            return True
        
        # Check persisted state
        return is_killswitch_active(self.db_path)
    
    def activate(
        self,
        job_seed: str,
        reason: str,
        activated_by: str = "system"
    ) -> KillSwitchState:
        """
        Activate kill-switch (ONE-WAY).
        
        This is intentionally hard to reverse.
        """
        state = KillSwitchState(
            active=True,
            activated_at=datetime.utcnow().isoformat(),
            activated_by=activated_by,
            reason=reason,
            job_seed=job_seed,
        )
        
        # Create flag file (for external watchdog)
        with open(self.killswitch_path, 'w') as f:
            json.dump(state.to_dict(), f, indent=2)
        
        # Persist to database
        persist_killswitch(job_seed, reason, self.db_path)
        
        # Log violation
        record_violation(
            violation_id=f"killswitch-{job_seed}",
            violation_type="KILLSWITCH_ACTIVATION",
            job_seed=job_seed,
            description=reason,
            evidence={"activated_by": activated_by},
            severity="critical",
            db_path=self.db_path
        )
        
        return state
    
    def get_state(self) -> KillSwitchState:
        """Get current kill-switch state."""
        if self.killswitch_path.exists():
            with open(self.killswitch_path, 'r') as f:
                data = json.load(f)
                return KillSwitchState(**data)
        
        return KillSwitchState(active=self.is_active())
    
    def request_reset(
        self,
        requested_by: str,
        reason: str,
        signature: str
    ) -> ResetRequest:
        """
        Request reset (requires multi-party approval).
        
        Returns the request which must be signed by others.
        """
        request_id = hashlib.sha256(
            f"{datetime.utcnow().isoformat()}:{requested_by}:{reason}".encode()
        ).hexdigest()[:16]
        
        request = ResetRequest(
            request_id=request_id,
            requested_at=datetime.utcnow().isoformat(),
            requested_by=requested_by,
            reason=reason,
            signatures=[signature],
        )
        
        # Save request
        request_file = self.reset_path / f"{request_id}.json"
        with open(request_file, 'w') as f:
            json.dump(request.to_dict(), f, indent=2)
        
        return request
    
    def sign_reset(self, request_id: str, signer: str, signature: str) -> Optional[ResetRequest]:
        """Add signature to reset request."""
        request_file = self.reset_path / f"{request_id}.json"
        
        if not request_file.exists():
            return None
        
        with open(request_file, 'r') as f:
            data = json.load(f)
        
        request = ResetRequest(**data)
        
        if signature not in request.signatures:
            request.signatures.append(signature)
        
        # Check if we have enough signatures
        if len(request.signatures) >= REQUIRED_RESET_SIGNATURES:
            request.approved = True
        
        # Save updated request
        with open(request_file, 'w') as f:
            json.dump(request.to_dict(), f, indent=2)
        
        return request
    
    def execute_reset(self, request_id: str) -> bool:
        """
        Execute approved reset.
        
        Returns True if reset was executed.
        """
        request_file = self.reset_path / f"{request_id}.json"
        
        if not request_file.exists():
            return False
        
        with open(request_file, 'r') as f:
            data = json.load(f)
        
        request = ResetRequest(**data)
        
        if not request.approved:
            return False
        
        # Remove kill-switch file
        if self.killswitch_path.exists():
            self.killswitch_path.unlink()
        
        # Update database
        set_guard_state("killswitch_active", "false", self.db_path)
        set_guard_state("killswitch_reset_at", datetime.utcnow().isoformat(), self.db_path)
        set_guard_state("killswitch_reset_request", request_id, self.db_path)
        
        return True


# =============================================================================
# HEARTBEAT FOR WATCHDOG
# =============================================================================

class HeartbeatMonitor:
    """
    Heartbeat for external watchdog monitoring.
    
    Watchdog should:
    - Check heartbeat file exists
    - Check timestamp is recent (< HEARTBEAT_INTERVAL * 2)
    - Activate kill-switch if heartbeat stale
    """
    
    def __init__(self, heartbeat_path: Path = None):
        self.heartbeat_path = heartbeat_path or DEFAULT_HEARTBEAT_FILE
        self.heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    
    def send_heartbeat(self, process_id: int, stage3_mode: str, healthy: bool = True):
        """Send heartbeat to watchdog."""
        heartbeat = Heartbeat(
            timestamp=datetime.utcnow().isoformat(),
            process_id=process_id,
            stage3_mode=stage3_mode,
            healthy=healthy,
        )
        
        with open(self.heartbeat_path, 'w') as f:
            json.dump(heartbeat.to_dict(), f)
    
    def get_last_heartbeat(self) -> Optional[Heartbeat]:
        """Get last heartbeat (for watchdog)."""
        if not self.heartbeat_path.exists():
            return None
        
        with open(self.heartbeat_path, 'r') as f:
            data = json.load(f)
            return Heartbeat(**data)
    
    def is_healthy(self, max_age_seconds: int = None) -> bool:
        """Check if heartbeat is recent."""
        if max_age_seconds is None:
            max_age_seconds = HEARTBEAT_INTERVAL * 2
        
        heartbeat = self.get_last_heartbeat()
        if heartbeat is None:
            return False
        
        # Parse timestamp and check age
        try:
            hb_time = datetime.fromisoformat(heartbeat.timestamp)
            age = (datetime.utcnow() - hb_time).total_seconds()
            return age < max_age_seconds and heartbeat.healthy
        except Exception:
            return False


# =============================================================================
# MODE TRANSITION AUDIT TRAIL
# =============================================================================

@dataclass
class ModeTransitionAudit:
    """
    P1 Item 11: Mode transitions produce auditable records.
    """
    transition_id: str
    from_mode: str
    to_mode: str
    
    # Signed intent
    signed_intent: str             # Human-readable justification
    intent_signature: str          # Cryptographic signature of intent
    
    # Preconditions snapshot
    preconditions: Dict            # State at transition time
    preconditions_hash: str        # Hash of preconditions
    
    # Approvals
    council_votes: List[str]       # Who approved
    admin_signature: str           # Admin signature
    
    # Timing
    requested_at: str
    approved_at: Optional[str] = None
    executed_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "transition_id": self.transition_id,
            "from_mode": self.from_mode,
            "to_mode": self.to_mode,
            "signed_intent": self.signed_intent,
            "intent_signature": self.intent_signature,
            "preconditions": self.preconditions,
            "preconditions_hash": self.preconditions_hash,
            "council_votes": self.council_votes,
            "admin_signature": self.admin_signature,
            "requested_at": self.requested_at,
            "approved_at": self.approved_at,
            "executed_at": self.executed_at,
        }
    
    def verify_preconditions_hash(self) -> bool:
        """Verify preconditions haven't changed."""
        expected = hashlib.sha256(
            json.dumps(self.preconditions, sort_keys=True).encode()
        ).hexdigest()[:32]
        return self.preconditions_hash == expected


def create_mode_transition_audit(
    from_mode: str,
    to_mode: str,
    signed_intent: str,
    preconditions: Dict,
    council_votes: List[str],
    admin_signature: str
) -> ModeTransitionAudit:
    """Create a mode transition audit record."""
    transition_id = hashlib.sha256(
        f"{from_mode}:{to_mode}:{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()[:16]
    
    preconditions_hash = hashlib.sha256(
        json.dumps(preconditions, sort_keys=True).encode()
    ).hexdigest()[:32]
    
    intent_signature = hashlib.sha256(
        signed_intent.encode()
    ).hexdigest()[:32]
    
    return ModeTransitionAudit(
        transition_id=transition_id,
        from_mode=from_mode,
        to_mode=to_mode,
        signed_intent=signed_intent,
        intent_signature=intent_signature,
        preconditions=preconditions,
        preconditions_hash=preconditions_hash,
        council_votes=council_votes,
        admin_signature=admin_signature,
        requested_at=datetime.utcnow().isoformat(),
    )
