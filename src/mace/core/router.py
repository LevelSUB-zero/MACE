from mace.core import deterministic

def route_percept(percept, qcp_snapshot):
    """
    Route a percept based on QCP snapshot.
    
    Args:
        percept (dict): The Percept object.
        qcp_snapshot (dict): The QCP snapshot from analyze_percept.
        
    Returns:
        dict: ExtendedRouterDecision object.
    """
    features = qcp_snapshot.get("features", {})
    
    # Determine agents and explanation
    selected_agents = []
    explain = "matched_R4_fallback"
    
    if features.get("math"):
        selected_agents = [{
            "agent_id": "math_agent",
            "role": "primary",
            "budget_tokens": 0
        }]
        explain = "matched_R1_math"
        
    elif features.get("profile"):
        selected_agents = [{
            "agent_id": "profile_agent",
            "role": "primary",
            "budget_tokens": 0
        }]
        explain = "matched_R2_profile"
        
    elif features.get("fact"):
        selected_agents = [{
            "agent_id": "knowledge_agent",
            "role": "primary",
            "budget_tokens": 0
        }]
        explain = "matched_R3_knowledge"
        
    else:
        selected_agents = [{
            "agent_id": "generic_agent",
            "role": "primary",
            "budget_tokens": 0
        }]
        explain = "matched_R4_fallback"
        
    # Generate deterministic ID
    # decision_id = deterministic_id("decision", percept_id, counter)
    # We need a counter for decisions? Spec doesn't explicitly name one, but implies it.
    # Let's use a "decision" counter or just re-use "id"?
    # Spec says: "decision_id: deterministic id".
    # Let's use a dedicated counter if possible, or just "id" counter.
    # Implementation plan said: deterministic.deterministic_id("decision", percept_id, counter)
    # Let's use "id" counter for simplicity as it's a general ID.
    # Or better, let's use a local counter if we want strict separation, but global "id" is fine.
    # Wait, deterministic.py has "id" counter.
    
    percept_id = percept.get("percept_id", "unknown_percept")
    
    # We need to increment a counter to ensure uniqueness if multiple decisions per percept (unlikely but possible).
    # But usually 1 decision per percept.
    # Let's use the global ID counter.
    decision_counter = deterministic.increment_counter("id")
    decision_id = deterministic.deterministic_id("decision", percept_id, decision_counter)
    
    created_at = deterministic.deterministic_timestamp(decision_counter)
    
    decision = {
        "decision_id": decision_id,
        "percept_id": percept_id,
        "selected_agents": selected_agents,
        "qcp_snapshot": qcp_snapshot,
        "router_features_used": list(features.keys()),
        "depth_level": qcp_snapshot.get("depth_level", 1),
        "memory_strategy": "sem_only",
        "memory_routing_decision": {},
        "budget": {
            "token_budget": 0,
            "time_budget_ms": 0,
            "cost_estimate": 0.0
        },
        "brainstate_snapshot": {},
        "fallback_policy": "generic_agent",
        "explain": explain,
        "created_at": created_at,
        "created_by": "router_stage0",
        "random_seed": deterministic.get_seed()
    }
    
    return decision
