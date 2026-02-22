"""
Knowledge Agent - Flexible Fact Storage and Retrieval

Uses intent_parser for flexible understanding.
Handles:
- "remember that X is Y" / "note that X means Y"
- "what is X" / "tell me about X"
"""
from mace.core import structures
from mace.memory import semantic


def run(percept):
    """Handle knowledge queries using pre-parsed NLU intent."""
    intent = percept.get("intent", "unknown")
    entities = percept.get("entities", {})
    
    attr = entities.get("attribute") or entities.get("topic")
    val = entities.get("value")
    
    # ===== TEACH FACT =====
    if intent in ["fact_teach", "fact_correction"]:
        if attr and val:
            key = f"world/fact/general/{attr}"
            result = semantic.put_sem(key, val, source="agent:knowledge_agent")
            
            if result["success"]:
                return structures.create_agent_output(
                    agent_id="knowledge_agent",
                    text=f"Got it! I'll remember that {attr.replace('_', ' ')} is {val}.",
                    confidence=1.0,
                    reasoning_trace=f"Stored fact: {key} = {val}"
                )
    
    # ===== QUERY FACT =====
    elif intent in ["history_search", "history_recall", "explainability_request", "fact_recall", "unknown"]:
        if attr:
            key = f"world/fact/general/{attr}"
            result = semantic.get_sem(key)
            
            if result["exists"]:
                return structures.create_agent_output(
                    agent_id="knowledge_agent",
                    text=result["value"],
                    confidence=1.0,
                    reasoning_trace=f"Found fact: {key}"
                )
            else:
                return structures.create_agent_output(
                    agent_id="knowledge_agent",
                    text=f"I don't know about '{attr.replace('_', ' ')}' yet. Teach me with 'remember that X is Y'!",
                    confidence=0.5,
                    reasoning_trace=f"Fact not found: {key}"
                )
    
    # Fallback
    return structures.create_agent_output(
        agent_id="knowledge_agent",
        text="I can learn facts! Tell me 'remember that X is Y' or ask 'what is X'.",
        confidence=0.3,
        reasoning_trace=f"Intent: {intent}, no action taken"
    )
