"""
Stage-1 Deterministic Router (STAGE-0 RULEBOOK Compliant)

Rules:
- R1: Math detection -> math_agent
- R2: Fact lookup / Teaching -> knowledge_agent
- R3: Personal memory / Contacts -> profile_agent
- R4: Conversation / Fallback -> generic_agent

Spec: docs/STAGE-0_RULEBOOK.md Section 4
Implementation via New MACE NLU Intents
"""

import datetime
from mace.core import deterministic, canonical


def _select_agent_for_intent(intent: str, available_agents: list) -> dict:
    """
    Select agent based on the structured MACE NLU intent.
    """
    # Map intents to agent IDs
    intent_map = {
        # Math
        "math": "math_agent",
        
        # Profile (User & Contacts & Preferences)
        "profile_store": "profile_agent",
        "profile_recall": "profile_agent",
        "preference_store": "profile_agent",
        "preference_recall": "profile_agent",
        "contact_store": "profile_agent",
        "contact_recall": "profile_agent",
        "state_inform": "profile_agent",
        
        # Knowledge (Facts & History)
        "fact_teach": "knowledge_agent",
        "fact_correction": "knowledge_agent",
        "history_recall": "knowledge_agent",
        "history_search": "knowledge_agent",
        "explainability_request": "knowledge_agent",
        
        # Task / Action (Fallback to generic_agent for now until there is a task_agent)
        "task_start": "generic_agent",
        "reminder_set": "generic_agent",
        
        # Conversation
        "greeting": "generic_agent",
        "thanks": "generic_agent",
        "chitchat": "generic_agent",
        "gibberish": "generic_agent",
        "unknown": "generic_agent",
    }
    
    target_id = intent_map.get(intent, "generic_agent")
    
    # Find matching agent in available list
    for agent in available_agents:
        if target_id in agent.get("module_id", ""):
            return agent
            
    # If specific target not found, try generic
    if target_id != "generic_agent":
        for agent in available_agents:
            if "generic" in agent.get("module_id", ""):
                return agent
                
    return None


def route(percept: dict, brainstate: dict, available_agents: list) -> dict:
    """
    Stage-1 Deterministic Router.
    
    Pipeline:
    1. Reads parsed intent from percept (populated by executor using ollama_nlu)
    2. Map intent to agent (R1-R4)
    3. Construct deterministic decision object
    """
    intent = percept.get("intent", "unknown")
    # For compatibility, assume confidence 1.0 since our NLU output doesn't supply it right now
    confidence = 1.0
    
    # Select agent
    selected_agent = _select_agent_for_intent(intent, available_agents)
    
    # Fallback if really nothing found (shouldn't happen with generic fallback)
    if not selected_agent:
        selected_agent = available_agents[0] if available_agents else {}
    
    agent_id = selected_agent.get("module_id", "unknown_agent")
    
    # Create decision
    decision_id = deterministic.deterministic_id("decision", percept.get("percept_id", "unknown"))
    
    decision = {
        "decision_id": decision_id,
        "selected_agents": [{"agent_id": agent_id, "confidence": confidence}],
        "reasoning": f"Routed based on NLU intent: {intent}",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "router_version": "stage1_nlu_v3"
    }
    
    # Canonicalize
    return decision
