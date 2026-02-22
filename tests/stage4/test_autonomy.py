
import sys
sys.path.insert(0, r"f:\MAIN PROJECTS\Mace\src")

import pytest
from mace.stage4.stage4_router import route_autonomous

def test_autonomous_routing():
    """
    Verifies Phase 4.3: The Switch.
    Ensures input is processed by ShadowCortex (Active Mode) without Stage 3.
    """
    percept = {"content": "Hello Autonomous World", "user_id": "tester"}
    qcp = {}
    
    # Call the new router
    result = route_autonomous(percept, qcp, job_seed="test_auto_001")
    
    # Assertions
    assert "router_version" in result
    assert result["router_version"] == "4.3.0_autonomous"
    
    assert "explain" in result
    assert "[STAGE 4 AUTONOMY]" in result["explain"]
    
    assert "stage4_trace" in result
    trace = result["stage4_trace"]
    assert "op" in trace
    assert "action" in trace
    assert "awareness" in trace
    
    # Check Action Structure
    action = trace["action"]
    assert "action_type" in action
    assert "payload" in action
    
    print("\n[SUCCESS] Autonomous Router Result:")
    print(result)

if __name__ == "__main__":
    test_autonomous_routing()
