import sys
sys.path.insert(0, r"f:\MAIN PROJECTS\Mace\src")
import pytest
from mace.stage3.stage3_router import stage3_route_with_advisory

def mock_base_router(percept, qcp):
    return {
        "decision_id": "mock_decision",
        "selected_agents": [{"agent_id": "mock_agent"}],
        "explain": "mock_explain"
    }

def test_shadow_cortex_active():
    """
    Verifies that the Shadow Cortex (Phase 4.1) is actively running
    and attaching traces to the router output.
    """
    percept = {"content": "Test input for shadow cortex", "user_id": "tester"}
    qcp = {}
    
    result = stage3_route_with_advisory(
        percept=percept,
        qcp_snapshot=qcp,
        base_router_fn=mock_base_router
    )
    
    # Assert Stage 3 extensions
    assert "stage3_advisory" in result
    
    # Assert Stage 4 Shadow Trace
    assert "stage4_shadow" in result
    trace = result["stage4_shadow"]
    
    # Check trace structure
    assert trace is not None
    assert trace["shadow_cortex_version"] == "4.1.0"
    assert "reptile_op" in trace
    assert "thought_trace" in trace
    assert "awareness" in trace  # The Mirror should be active
    
    # Check if awareness worked (Stub should return NORMAL)
    awareness = trace["awareness"]
    assert isinstance(awareness, list)
    assert len(awareness) > 0
    assert awareness[0]["type"] == "normal" or awareness[0]["type"] == "uncertainty"

    print("\n[SUCCESS] Shadow Cortex Trace Captured:")
    print(trace)

if __name__ == "__main__":
    test_shadow_cortex_active()
