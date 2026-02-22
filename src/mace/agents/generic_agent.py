"""
Generic Agent - Conversational Handler

Uses intent_parser for flexible greetings, thanks, help, etc.
"""
import random
from mace.core import structures


GREETINGS = [
    "Hello! How can I help?",
    "Hi there! What can I do for you?",
    "Hey! I'm here to help.",
]

HELP_RESPONSES = [
    "I can help with math ('2+2'), remember things ('my name is X'), and facts ('what is pi'). What would you like?",
    "Try: math ('15 * 3'), profile ('remember my city is Tokyo'), or facts ('what is gravity').",
]

THANKS_RESPONSES = [
    "You're welcome!",
    "Happy to help!",
    "Anytime!",
]

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "There are 10 types of people: those who understand binary and those who don't.",
    "Why did the AI go to therapy? Too many deep issues!",
]

FALLBACK = [
    "I'm not sure about that. I can help with math, profile info, or facts!",
    "Hmm, try asking me to calculate something or remember something about you.",
]


def run(percept):
    """Handle general conversation."""
    text = percept["text"].strip()
    intent = percept.get("intent", "unknown")
    
    # Empty input
    if not text:
        return structures.create_agent_output(
            agent_id="generic_agent",
            text="I didn't catch that. What would you like to know?",
            confidence=1.0,
            reasoning_trace="Empty input"
        )
    
    # Greetings
    if intent == "greeting":
        return structures.create_agent_output(
            agent_id="generic_agent",
            text=random.choice(GREETINGS),
            confidence=1.0,
            reasoning_trace="Greeting"
        )
    
    # Thanks
    if intent == "thanks":
        return structures.create_agent_output(
            agent_id="generic_agent",
            text=random.choice(THANKS_RESPONSES),
            confidence=1.0,
            reasoning_trace="Thanks"
        )
    
    # Help
    if intent == "help" or "help" in text.lower():
        return structures.create_agent_output(
            agent_id="generic_agent",
            text=random.choice(HELP_RESPONSES),
            confidence=1.0,
            reasoning_trace="Help request"
        )
    
    # Jokes
    if "joke" in text.lower() or intent == "chitchat":
        return structures.create_agent_output(
            agent_id="generic_agent",
            text=random.choice(JOKES),
            confidence=1.0,
            reasoning_trace="Joke request/chitchat"
        )
    
    # How are you
    if "how are you" in text.lower():
        return structures.create_agent_output(
            agent_id="generic_agent",
            text="I'm running well! How can I help you?",
            confidence=1.0,
            reasoning_trace="How are you"
        )
    
    # Fallback
    return structures.create_agent_output(
        agent_id="generic_agent",
        text=random.choice(FALLBACK),
        confidence=0.5,
        reasoning_trace="Fallback"
    )
