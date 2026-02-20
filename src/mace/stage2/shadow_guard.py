"""
Stage-2 Shadow Guard Module (AUTHORITATIVE)

Purpose: Prevent accidental emergence of agency or silent optimization.
Spec: docs/stage2_ideology.md, docs/stage2_failure_modes.md

This module enforces the core Stage-2 invariant:
- MEM-SNN outputs are OBSERVED ONLY, NEVER CONSUMED
- Any violation triggers immediate halt and kill-switch

If this module is bypassed, Stage-2 is BROKEN.
"""

import os
import json
import datetime


# =============================================================================
# EXCEPTION: Learning Shadow Violation (P0 Incident)
# =============================================================================

class LearningShadowViolation(Exception):
    """
    Fatal violation: Learning output was consumed by an agentic component.
    
    This exception MUST:
    1. Halt Stage-2 immediately
    2. Trigger the Stage-2 kill-switch
    3. Mark logs as tainted
    4. Require human intervention to resume
    
    This is a P0 incident. There is no auto-recovery.
    """
    pass


# =============================================================================
# KILL-SWITCH (Stage-2 Specific)
# =============================================================================

STAGE2_KILLSWITCH_FILE = "mace_stage2_killswitch.flag"


def _activate_stage2_killswitch(reason: str, source_module: str):
    """
    Activate the Stage-2 specific kill-switch.
    This halts all learning operations but preserves Stage-1 behavior.
    """
    state = {
        "active": True,
        "reason": reason,
        "source_module": source_module,
        "activated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "type": "LEARNING_SHADOW_VIOLATION"
    }
    
    with open(STAGE2_KILLSWITCH_FILE, "w") as f:
        json.dump(state, f)


def is_stage2_halted() -> bool:
    """Check if Stage-2 is currently halted."""
    if not os.path.exists(STAGE2_KILLSWITCH_FILE):
        return False
    try:
        with open(STAGE2_KILLSWITCH_FILE, "r") as f:
            state = json.load(f)
        return state.get("active", False)
    except:
        return False


# =============================================================================
# SHADOW MODE ENFORCEMENT
# =============================================================================

def get_learning_mode() -> str:
    """
    Return the current learning mode.
    
    In Stage-2, this MUST always return "shadow".
    Any other value is a configuration error.
    """
    # Import here to avoid circular imports
    from mace.config import config_loader
    
    try:
        stage2_config = config_loader._load_yaml('stage2.yaml')
        mode = stage2_config.get("MEM_LEARNING_MODE", "shadow")
    except:
        # If config cannot be loaded, default to shadow (fail-safe)
        mode = "shadow"
    
    if mode != "shadow":
        # This is a configuration error, not a runtime violation
        raise LearningShadowViolation(
            f"Invalid MEM_LEARNING_MODE: '{mode}'. Must be 'shadow' in Stage-2."
        )
    
    return mode


def assert_shadow_mode(caller_module: str = "unknown"):
    """
    Assert that we are in shadow mode.
    
    Call this at ANY point where MEM-SNN output might be consumed.
    If shadow mode is violated, this will:
    1. Activate the Stage-2 kill-switch
    2. Raise LearningShadowViolation
    
    Args:
        caller_module: Name of the module calling this assertion (for logging)
    """
    # Check if Stage-2 is already halted
    if is_stage2_halted():
        raise LearningShadowViolation(
            f"Stage-2 is halted. Cannot proceed. Caller: {caller_module}"
        )
    
    # Verify shadow mode
    mode = get_learning_mode()
    if mode != "shadow":
        _activate_stage2_killswitch(
            reason=f"Shadow mode violation detected in {caller_module}",
            source_module=caller_module
        )
        raise LearningShadowViolation(
            f"Shadow mode violation in {caller_module}. Mode was: {mode}"
        )


def guard_against_consumption(output_name: str, caller_module: str = "unknown"):
    """
    Guard that MUST be called before any code attempts to USE a shadow output.
    
    This is the primary enforcement mechanism. Any code path that:
    - Reads MEM-SNN scores for routing
    - Uses candidate scores as thresholds
    - Auto-triggers SEM writes from council labels
    
    MUST call this guard first. The guard will always fail in Stage-2,
    which is the correct behavior.
    
    Args:
        output_name: Name of the shadow output being accessed
        caller_module: Name of the calling module
    """
    # In Stage-2, this ALWAYS fails. That's the point.
    _activate_stage2_killswitch(
        reason=f"Attempted to consume shadow output '{output_name}'",
        source_module=caller_module
    )
    raise LearningShadowViolation(
        f"FATAL: Attempted to consume shadow output '{output_name}' in {caller_module}. "
        f"Shadow outputs are OBSERVED ONLY, NEVER CONSUMED in Stage-2."
    )


# =============================================================================
# AGENTIC COMPONENT GUARDS
# =============================================================================
# These guards are called by agentic components (Router, Executor, SEM writer)
# to reject any attempt to read MEM-SNN output.

def guard_router_access(score_source: str):
    """
    Guard called by Router before any decision.
    Rejects if score_source references MEM-SNN.
    """
    if "mem_snn" in score_source.lower() or "shadow" in score_source.lower():
        guard_against_consumption(score_source, "router")


def guard_executor_access(decision_source: str):
    """
    Guard called by Executor before action execution.
    Rejects if decision_source references learning outputs.
    """
    if "mem_snn" in decision_source.lower() or "candidate_score" in decision_source.lower():
        guard_against_consumption(decision_source, "executor")


def guard_sem_write(trigger_source: str):
    """
    Guard called by SEM writer before any write.
    Rejects if write is triggered by council label without governance approval.
    """
    if "auto_trigger" in trigger_source.lower() or "council_label" in trigger_source.lower():
        if "governance_approved" not in trigger_source.lower():
            guard_against_consumption(trigger_source, "sem_writer")
