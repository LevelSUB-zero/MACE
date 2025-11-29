import re
from mace.core import structures

# Regex patterns
REGEX_MATH = re.compile(r"^\s*\d+\s*([+\-*/^])\s*\d+\s*$")
REGEX_PROFILE = re.compile(r"(my favorite|remember my)", re.IGNORECASE)
REGEX_FACT = re.compile(r"^(what is|define|who is|when was|where is)", re.IGNORECASE)

def route(percept, brainstate_snapshot):
    """
    Deterministic routing logic for Stage-0.
    Returns an ExtendedRouterDecision object.
    """
    text = percept["text"].strip()
    
    # R1 - Math
    if REGEX_MATH.match(text):
        agent_id = "math_agent"
        why = "matched_R1_math"
        features = ["regex_match_R1"]
        
    # R2 - Profile
    elif REGEX_PROFILE.search(text):
        agent_id = "profile_agent"
        why = "matched_R2_profile"
        features = ["regex_match_R2"]
        
    # R3 - Knowledge
    elif REGEX_FACT.match(text):
        agent_id = "knowledge_agent"
        why = "matched_R3_knowledge"
        features = ["regex_match_R3"]
        
    # R4 - Fallback
    else:
        agent_id = "generic_agent"
        why = "matched_R4_fallback"
        features = ["rule_match_fallback"]
        
    # Create decision object
    selected_agents = [
        {
            "agent_id": agent_id,
            "role": "primary",
            "budget_tokens": 0
        }
    ]
    
    return structures.create_router_decision(
        percept_id=percept["percept_id"],
        selected_agents=selected_agents,
        why=why,
        router_features_used=features,
        brainstate_snapshot=brainstate_snapshot
    )
