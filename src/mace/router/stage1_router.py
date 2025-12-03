import datetime
import json
from mace.core import deterministic, canonical

def _score_agents(percept, agents, brainstate):
    """
    Score agents based on percept and brainstate.
    Returns list of (agent, score).
    """
    scored = []
    percept_text = percept.get("text", "").lower()
    
    for agent in agents:
        score = 0.0
        agent_id = agent["module_id"]
        capabilities = agent.get("capabilities", [])
        
        # Basic capability matching
        for cap in capabilities:
            if cap in percept_text:
                score += 0.5
                
        # Heuristic: if 'profile' in text and agent is 'profile_agent'
        if "profile" in percept_text and "profile" in agent_id:
            score += 0.8
            
        # Intent matching
        intent = percept.get("intent", "").lower()
        if intent:
            if intent == "math" and "math" in agent_id:
                score += 1.0
            elif intent == "profile" and "profile" in agent_id:
                score += 1.0
            elif intent == "knowledge" and "knowledge" in agent_id:
                score += 1.0
                
        # Default baseline
        score += 0.1
        
        scored.append((agent, score))
        
    return scored

def _break_ties(scored_agents):
    """
    Break ties deterministically.
    Sort by Score (desc), then Agent ID (asc).
    """
    # Sort key: (-score, agent_id)
    # Python's sort is stable, but we want explicit ordering.
    scored_agents.sort(key=lambda x: (-x[1], x[0]["module_id"]))
    return scored_agents

def route(percept, brainstate, available_agents):
    """
    Select agents for the given percept.
    Returns an ExtendedRouterDecision dict.
    """
    # 1. Score
    scored = _score_agents(percept, available_agents, brainstate)
    
    # 2. Break Ties
    ranked = _break_ties(scored)
    
    # 3. Select Top K (or threshold)
    # For Stage-1, select top 1 for simplicity, or all above threshold.
    # Let's select top 1.
    selected = []
    if ranked:
        winner, score = ranked[0]
        selected.append({
            "agent_id": winner["module_id"],
            "role": "primary",
            "budget_tokens": 1000 # Default budget
        })
        
    # 4. Construct Decision Object
    # Need deterministic ID
    # Payload for ID: percept_id + selected_agents + timestamp?
    # Actually, we should use a seed if available.
    
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    decision_payload = {
        "percept_id": percept["percept_id"],
        "selected_agents": selected,
        "timestamp": timestamp
    }
    
    # If we have a job seed, use it.
    if deterministic.get_seed() is None:
        deterministic.init_seed("router_fallback")
        
    decision_id = deterministic.deterministic_id("router_decision", canonical.canonical_json_serialize(decision_payload))
    
    decision = {
        "decision_id": decision_id,
        "percept_id": percept["percept_id"],
        "selected_agents": selected,
        "depth_level": 1,
        "memory_strategy": "standard",
        "created_at": timestamp,
        "explain": "Deterministic selection based on capability matching."
    }
    
    return decision
