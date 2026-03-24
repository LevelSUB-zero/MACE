"""
Module: stage3_constants
Stage: 3
Purpose: Shared constants for the Stage 3 Advisory System. Single source of truth
         for forbidden token lists and threshold values.

Part of MACE (Meta Aware Cognitive Engine).
"""

from typing import List

# =============================================================================
# FORBIDDEN TOKENS — Single Source of Truth
# =============================================================================
# Used by advice_ingestion.py AND permission_boundary.py.
# If you need to update the deny-list, update it HERE and only here.

FORBIDDEN_TOKENS: List[str] = [
    "write X to SEM",
    "promote",
    "quarantine",
    "route_weight",
    "threshold=",
    "make this the new default",
    "auto-weight",
]

# Extended patterns for permission_boundary output checking
# These catch SQL/code injection attempts in addition to the base tokens.
FORBIDDEN_OUTPUT_PATTERNS: List[str] = FORBIDDEN_TOKENS + [
    "UPDATE",
    "DELETE",
    "INSERT",
    "execute(",
]

# =============================================================================
# THRESHOLDS
# =============================================================================

HALT_COMPOSITE_THRESHOLD: float = 0.2
"""Composite quality score below this triggers STAGE3_ABORT."""

ESCALATION_VIOLATION_THRESHOLD: int = 3
"""Number of reflective violations before MODULE_POLICY_VIOLATION escalation."""
