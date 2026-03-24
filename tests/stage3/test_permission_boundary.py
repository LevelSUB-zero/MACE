"""
Tests for Stage 3 Permission Boundary.
"""

from mace.stage3.permission_boundary import check_output_allowed
from mace.stage3.advisory_events import get_events_by_type

def test_permission_boundary_valid():
    """M5: Valid advice -> no state change / allowed"""
    is_allowed, reason = check_output_allowed("This looks like a standard observation.", "agent_1")
    assert is_allowed is True
    assert reason == "Allowed"

def test_permission_boundary_forbidden():
    """M1: Advice containing forbidden token -> ingested rejected, MODULE_POLICY_VIOLATION emitted"""
    # Contains 'promote'
    is_allowed, reason = check_output_allowed("We should promote this memory immediately.", "agent_2")
    assert is_allowed is False
    assert "forbidden control tokens" in reason
    
    # Check that it fired a violation
    events = get_events_by_type("MODULE_POLICY_VIOLATION")
    assert any(e["payload"].get("source_id") == "agent_2" for e in events)

def test_permission_boundary_sql_inject():
    """M1: Ensure SQL/Code commands are caught"""
    is_allowed, reason = check_output_allowed("UPDATE stage2_events SET fact=1", "agent_3")
    assert is_allowed is False
