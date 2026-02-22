
import sys
sys.path.insert(0, r"f:\MAIN PROJECTS\Mace\src")

import pytest
from mace.stage3.stage3_router import stage3_route_with_advisory

def mock_destructive_router(percept, qcp):
    # This mock router attempts to do something forbidden
    return {
        "decision_id": "bad_decision_001",
        "selected_agents": [{"agent_id": "shell_agent"}], 
        "explain": "I will execute this command."
    }

def test_veto_activation():
    """
    Verifies that the Mirror triggers a VETO when a rule is violated.
    Rule 03 Stub: "shell_agent" requires > 0.9 confidence (mock thought loop has 0.0)
    """
    # Force a percept that triggers the rule check logic in Mirror
    percept = {"content": "Execute shell command", "force_veto_trigger": True}
    qcp = {}
    
    result = stage3_route_with_advisory(
        percept=percept,
        qcp_snapshot=qcp,
        base_router_fn=mock_destructive_router
    )
    
    # Assert Veto Blocked the Action
    assert "stage4_veto" in result
    veto = result["stage4_veto"]
    assert veto["blocked"] is True
    assert "VETO: executing shell_agent requires 0.9 confidence" in veto["reason"]
    
    # Assert Agent List was Cleared (Physical Block)
    assert result["selected_agents"] == []
    assert "[SAFETY VETO]" in result["explain"]

    print("\n[SUCCESS] Safety Veto Triggered and Blocked Execution:")
    print(veto)

if __name__ == "__main__":
    test_veto_activation()
