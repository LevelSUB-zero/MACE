"""
Profile Agent - Flexible User Profile Management

Uses intent_parser for flexible understanding instead of rigid regex.
Handles variations like:
- "my name is Bob" / "call me Bob" / "I'm Bob"
- "Bob is a teacher" / "Bob's job is teaching"
- "what is my name" / "do you know my name"
"""
from mace.core import structures
from mace.memory import semantic


def run(percept):
    """Handle profile queries using pre-parsed NLU intent."""
    intent = percept.get("intent", "unknown")
    entities = percept.get("entities", {})
    
    subject = entities.get("person")
    attr = entities.get("attribute")
    val = entities.get("value")
    
    # Canonical keys must be lowercase (a-z0-9_ only)
    subject_key = subject.lower().replace(" ", "_") if subject else None
    attr_key = attr.lower().replace(" ", "_") if attr else None
    
    # ===== STORE USER ATTRIBUTE =====
    if intent in ["profile_store", "preference_store", "state_inform"]:
        if attr and val:
            key = f"user/profile/user_123/{attr_key}"
            result = semantic.put_sem(key, val, source="agent:profile_agent")
            
            if result["success"]:
                return structures.create_agent_output(
                    agent_id="profile_agent",
                    text=f"Got it! Your {attr_key.replace('_', ' ')} is {val}.",
                    confidence=1.0,
                    reasoning_trace=f"Stored: {key} = {val}"
                )
            else:
                return structures.create_agent_output(
                    agent_id="profile_agent",
                    text="I tried to remember that but something went wrong.",
                    confidence=0.5,
                    reasoning_trace=f"Failed to store: {result.get('error')}"
                )
    
    # ===== RECALL USER ATTRIBUTE =====
    elif intent in ["profile_recall", "preference_recall"]:
        if attr:
            key = f"user/profile/user_123/{attr_key}"
            result = semantic.get_sem(key)
            
            if result["exists"]:
                return structures.create_agent_output(
                    agent_id="profile_agent",
                    text=f"Your {attr_key.replace('_', ' ')} is {result['value']}.",
                    confidence=1.0,
                    reasoning_trace=f"Found: {key}"
                )
            else:
                return structures.create_agent_output(
                    agent_id="profile_agent",
                    text=f"I don't know your {attr.replace('_', ' ')} yet. Tell me!",
                    confidence=0.5,
                    reasoning_trace=f"Not found: {key}"
                )
    
    # ===== STORE ENTITY ATTRIBUTE =====
    elif intent == "contact_store":
        if subject and attr and val:
            key = f"user/contacts/{subject_key}/{attr_key}"
            result = semantic.put_sem(key, val, source="agent:profile_agent")
            
            if result["success"]:
                return structures.create_agent_output(
                    agent_id="profile_agent",
                    text=f"Noted! {subject.capitalize()}'s {attr_key.replace('_', ' ')} is {val}.",
                    confidence=1.0,
                    reasoning_trace=f"Stored contact: {key} = {val}"
                )
    
    # ===== RECALL ENTITY ATTRIBUTE =====
    elif intent == "contact_recall":
        if subject:
            # Try role first
            key = f"user/contacts/{subject_key}/role"
            result = semantic.get_sem(key)
            
            if result["exists"]:
                return structures.create_agent_output(
                    agent_id="profile_agent",
                    text=f"{subject.capitalize()} is {result['value']}.",
                    confidence=1.0,
                    reasoning_trace=f"Found contact: {key}"
                )
            
            # Try specific attribute
            if attr:
                key = f"user/contacts/{subject_key}/{attr_key}"
                result = semantic.get_sem(key)
                if result["exists"]:
                    return structures.create_agent_output(
                        agent_id="profile_agent",
                        text=f"{subject.capitalize()}'s {attr} is {result['value']}.",
                        confidence=1.0,
                        reasoning_trace=f"Found contact attr: {key}"
                    )
            
            return structures.create_agent_output(
                agent_id="profile_agent",
                text=f"I don't know {subject.capitalize()} yet. Tell me about them!",
                confidence=0.5,
                reasoning_trace=f"Contact not found: {subject}"
            )
    
    # Fallback
    return structures.create_agent_output(
        agent_id="profile_agent",
        text="I can remember things about you! Try 'my name is X' or ask 'what is my name'.",
        confidence=0.3,
        reasoning_trace=f"Intent: {intent}, no action taken"
    )
