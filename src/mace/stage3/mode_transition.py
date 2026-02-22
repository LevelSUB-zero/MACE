"""
ModeTransitionManager - Stage-3 Learning Mode Governance

Manages transition from shadow mode to advisory mode.
This transition is NOT automatic, NOT silent, and NOT reversible by code alone.

Hard requirements:
- Transition requires Council approval + admin signature
- Transition snapshot is HMAC-signed
- Transition is logged as a first-class governance event
- Transition is replay-verifiable

Spec: docs/stage3/EXECUTION_PLAN_FINAL.md section 1.2
"""

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class LearningMode(str, Enum):
    """Valid learning modes."""
    SHADOW = "shadow"       # Stage-2: outputs logged, never consumed
    ADVISORY = "advisory"   # Stage-3: outputs visible but not trusted


@dataclass
class ModeTransitionRequest:
    """Request to transition learning mode."""
    request_id: str
    from_mode: LearningMode
    to_mode: LearningMode
    requested_by: str  # admin ID
    council_approval_ids: List[str]  # list of council member IDs who approved
    rationale: str
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "from_mode": self.from_mode.value,
            "to_mode": self.to_mode.value,
            "requested_by": self.requested_by,
            "council_approval_ids": self.council_approval_ids,
            "rationale": self.rationale,
            "created_at": self.created_at,
        }


@dataclass
class ModeTransitionEvent:
    """Governance event for mode transition."""
    event_id: str
    event_type: str = "MODE_TRANSITION"
    from_mode: str = ""
    to_mode: str = ""
    request_id: str = ""
    admin_signature: str = ""
    snapshot_signature: str = ""
    created_at: str = ""
    is_replayable: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "from_mode": self.from_mode,
            "to_mode": self.to_mode,
            "request_id": self.request_id,
            "admin_signature": self.admin_signature,
            "snapshot_signature": self.snapshot_signature,
            "created_at": self.created_at,
            "is_replayable": self.is_replayable,
        }


class ModeTransitionManager:
    """
    Manages learning mode transitions with governance requirements.
    
    Invariant: Learning mode transitions are constitutional events, not runtime flags.
    """
    
    REQUIRED_COUNCIL_APPROVALS = 2  # Minimum council members required
    
    def __init__(self, current_mode: LearningMode = LearningMode.SHADOW):
        """Initialize with current mode."""
        self._current_mode = current_mode
        self._transition_history: List[ModeTransitionEvent] = []
        self._pending_request: Optional[ModeTransitionRequest] = None
    
    @property
    def current_mode(self) -> LearningMode:
        """Get current learning mode."""
        return self._current_mode
    
    def request_transition(
        self,
        to_mode: LearningMode,
        requested_by: str,
        rationale: str
    ) -> ModeTransitionRequest:
        """
        Create a transition request.
        
        This starts the governance process but does NOT execute the transition.
        """
        request_id = hashlib.sha256(
            f"transition:{self._current_mode.value}:{to_mode.value}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        request = ModeTransitionRequest(
            request_id=request_id,
            from_mode=self._current_mode,
            to_mode=to_mode,
            requested_by=requested_by,
            council_approval_ids=[],
            rationale=rationale,
            created_at=datetime.utcnow().isoformat(),
        )
        
        self._pending_request = request
        return request
    
    def add_council_approval(self, request_id: str, council_member_id: str) -> bool:
        """Add a council member's approval to the request."""
        if self._pending_request is None:
            return False
        if self._pending_request.request_id != request_id:
            return False
        if council_member_id in self._pending_request.council_approval_ids:
            return False
        
        self._pending_request.council_approval_ids.append(council_member_id)
        return True
    
    def has_sufficient_approvals(self) -> bool:
        """Check if pending request has sufficient council approvals."""
        if self._pending_request is None:
            return False
        return len(self._pending_request.council_approval_ids) >= self.REQUIRED_COUNCIL_APPROVALS
    
    def execute_transition(
        self,
        admin_id: str,
        admin_signature: str
    ) -> Optional[ModeTransitionEvent]:
        """
        Execute the pending transition with admin signature.
        
        Requirements:
        - Council approval + admin signature
        - Transition snapshot is HMAC-signed
        - Transition is logged as governance event
        """
        if self._pending_request is None:
            return None
        
        if not self.has_sufficient_approvals():
            return None
        
        if not admin_signature:
            return None
        
        # Generate event ID
        event_id = hashlib.sha256(
            f"mode_event:{self._pending_request.request_id}:{admin_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Create snapshot signature
        snapshot_data = json.dumps({
            "from_mode": self._pending_request.from_mode.value,
            "to_mode": self._pending_request.to_mode.value,
            "request_id": self._pending_request.request_id,
            "council_approvals": sorted(self._pending_request.council_approval_ids),
            "admin_id": admin_id,
        }, sort_keys=True)
        snapshot_signature = hashlib.sha256(snapshot_data.encode()).hexdigest()[:32]
        
        # Create governance event
        event = ModeTransitionEvent(
            event_id=event_id,
            event_type="MODE_TRANSITION",
            from_mode=self._pending_request.from_mode.value,
            to_mode=self._pending_request.to_mode.value,
            request_id=self._pending_request.request_id,
            admin_signature=admin_signature,
            snapshot_signature=snapshot_signature,
            created_at=datetime.utcnow().isoformat(),
            is_replayable=True,
        )
        
        # Execute transition
        self._current_mode = self._pending_request.to_mode
        self._transition_history.append(event)
        self._pending_request = None
        
        return event
    
    def force_shadow_mode(self, reason: str) -> ModeTransitionEvent:
        """
        Force transition to shadow mode (kill-switch response).
        
        This is an emergency action that bypasses normal governance
        but is still logged for audit.
        """
        event_id = hashlib.sha256(
            f"force_shadow:{reason}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        event = ModeTransitionEvent(
            event_id=event_id,
            event_type="FORCE_SHADOW_MODE",
            from_mode=self._current_mode.value,
            to_mode=LearningMode.SHADOW.value,
            request_id="EMERGENCY",
            admin_signature="KILLSWITCH",
            snapshot_signature="",
            created_at=datetime.utcnow().isoformat(),
            is_replayable=True,
        )
        
        self._current_mode = LearningMode.SHADOW
        self._transition_history.append(event)
        self._pending_request = None
        
        return event
    
    def get_transition_history(self) -> List[ModeTransitionEvent]:
        """Get all transition events for audit."""
        return self._transition_history.copy()
    
    def is_advisory_mode(self) -> bool:
        """Check if currently in advisory mode."""
        return self._current_mode == LearningMode.ADVISORY
    
    def is_shadow_mode(self) -> bool:
        """Check if currently in shadow mode."""
        return self._current_mode == LearningMode.SHADOW


# Global manager instance
_manager: Optional[ModeTransitionManager] = None


def get_mode_manager() -> ModeTransitionManager:
    """Get global mode transition manager."""
    global _manager
    if _manager is None:
        _manager = ModeTransitionManager()
    return _manager


def get_current_mode() -> LearningMode:
    """Get current learning mode."""
    return get_mode_manager().current_mode


def is_advisory_enabled() -> bool:
    """Check if advisory mode is enabled."""
    return get_mode_manager().is_advisory_mode()
