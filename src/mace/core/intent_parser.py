"""
Flexible Intent Parser for MACE Agents

Uses keyword detection and intent scoring instead of rigid regex.
This allows understanding natural language variations.

Example variations it handles:
- "my name is Bob" / "call me Bob" / "I'm Bob" / "Bob is my name"
- "what's my name" / "do you know my name" / "tell me my name"
"""
from typing import Dict, List, Optional, Tuple
import re


class IntentType:
    """Flexible intent categories."""
    STORE_USER_ATTR = "store_user_attr"      # User wants to save something about themselves
    RECALL_USER_ATTR = "recall_user_attr"    # User wants to know something about themselves
    STORE_ENTITY_ATTR = "store_entity_attr"  # User stores info about a third party
    RECALL_ENTITY_ATTR = "recall_entity_attr"# User recalls info about a third party
    TEACH_FACT = "teach_fact"                # User teaches a world fact
    QUERY_FACT = "query_fact"                # User queries a world fact
    MATH = "math"                            # Math calculation
    GREETING = "greeting"                    # Greeting
    THANKS = "thanks"                        # Thanks
    HELP = "help"                            # Help request
    UNKNOWN = "unknown"                      # Fallback


# Flexible keyword sets
STORE_KEYWORDS = {"remember", "save", "note", "store", "keep", "set", "my", "i'm", "im", "i am", "call me"}
RECALL_KEYWORDS = {"what", "tell", "show", "get", "recall", "know", "do you know", "what's", "whats"}
PERSONAL_INDICATORS = {"my", "i", "me", "i'm", "im", "mine"}
ENTITY_INDICATORS = {"is a", "is an", "'s", "s'"}  # "Bob is a teacher", "Bob's"
FACT_INDICATORS = {"means", "is defined as", "equals", "="}
QUESTION_INDICATORS = {"?", "what", "who", "where", "when", "how", "why", "tell me", "do you know"}
MATH_INDICATORS = {"+", "-", "*", "/", "plus", "minus", "times", "divided", "multiply", "calculate", "compute"}
GREETING_WORDS = {"hello", "hi", "hey", "good morning", "good evening", "good afternoon", "greetings"}
THANKS_WORDS = {"thank", "thanks", "thx", "ty", "appreciate"}
HELP_WORDS = {"help", "what can you", "capabilities", "what do you do"}

# Common attributes (not exhaustive - any word can be an attribute)
COMMON_ATTRS = {
    "name", "age", "color", "colour", "city", "job", "work", "occupation",
    "food", "hobby", "pet", "friend", "brother", "sister", "mother", "father",
    "favorite", "favourite", "birthday", "email", "phone", "address"
}


def parse_intent(text: str) -> Dict:
    """
    Parse user input and detect intent flexibly.
    
    Returns:
        {
            "intent": IntentType,
            "confidence": float,
            "subject": str | None,      # e.g., "user" or "Bob"
            "attribute": str | None,    # e.g., "name", "favorite_color"
            "value": str | None,        # e.g., "Alice"
            "raw_text": str
        }
    """
    if not text or not text.strip():
        return {"intent": IntentType.UNKNOWN, "confidence": 0.0, "raw_text": text}
    
    text = text.strip()
    text_lower = text.lower()
    words = set(text_lower.split())
    
    result = {
        "intent": IntentType.UNKNOWN,
        "confidence": 0.0,
        "subject": None,
        "attribute": None,
        "value": None,
        "raw_text": text
    }
    
    # Check for math first (highest priority for explicit math)
    if _is_math(text_lower):
        result["intent"] = IntentType.MATH
        result["confidence"] = 0.9
        return result
    
    # Check for greetings (whole words or phrases)
    if any(g in words for g in GREETING_WORDS) or \
       any(phrase in text_lower for phrase in ["good morning", "good evening", "good afternoon"]):
        result["intent"] = IntentType.GREETING
        result["confidence"] = 0.9
        return result
    
    # Check for thanks
    if any(t in words for t in THANKS_WORDS):
        result["intent"] = IntentType.THANKS
        result["confidence"] = 0.9
        return result
    
    # Check for help
    if any(h in words for h in HELP_WORDS) or \
       any(phrase in text_lower for phrase in ["what can you", "what do you"]):
        result["intent"] = IntentType.HELP
        result["confidence"] = 0.9
        return result
    
    # Detect if this is a question
    is_question = any(q in words for q in QUESTION_INDICATORS) or "?" in text
    
    # Detect if personal (about user)
    is_personal = any(p in words for p in PERSONAL_INDICATORS)
    
    # Detect if about a third party entity
    entity_name = _extract_entity(text)
    
    # Detect if it's a store/teach operation
    is_store = any(s in words for s in STORE_KEYWORDS) or " is " in text_lower
    
    # Parse based on detected signals
    if is_question:
        # It's a recall/query
        if is_personal:
            result["intent"] = IntentType.RECALL_USER_ATTR
            result["subject"] = "user"
            result["attribute"] = _extract_attribute(text_lower)
            result["confidence"] = 0.8
        elif entity_name:
            result["intent"] = IntentType.RECALL_ENTITY_ATTR
            result["subject"] = entity_name
            result["attribute"] = _extract_attribute(text_lower)
            result["confidence"] = 0.7
        else:
            result["intent"] = IntentType.QUERY_FACT
            result["attribute"] = _extract_query_subject(text_lower)
            result["confidence"] = 0.6
    
    elif is_store:
        # It's a store/teach operation
        if is_personal:
            result["intent"] = IntentType.STORE_USER_ATTR
            result["subject"] = "user"
            attr, val = _extract_attr_value(text, is_personal=True)
            result["attribute"] = attr
            result["value"] = val
            result["confidence"] = 0.8
        elif entity_name:
            result["intent"] = IntentType.STORE_ENTITY_ATTR
            result["subject"] = entity_name
            attr, val = _extract_attr_value(text, entity_name=entity_name)
            result["attribute"] = attr
            result["value"] = val
            result["confidence"] = 0.7
        else:
            result["intent"] = IntentType.TEACH_FACT
            attr, val = _extract_fact(text)
            result["attribute"] = attr
            result["value"] = val
            result["confidence"] = 0.6
    
    return result


def _is_math(text: str) -> bool:
    """Check if text is a math expression."""
    # Has math operators or keywords
    if any(m in text for m in MATH_INDICATORS):
        return True
    # Looks like a number expression
    if re.search(r'\d+\s*[\+\-\*\/]\s*\d+', text):
        return True
    return False


def _extract_entity(text: str) -> Optional[str]:
    """Extract a named entity (third party person/thing)."""
    # Look for capitalized words that aren't at sentence start
    words = text.split()
    if len(words) < 2:
        return None
    
    # Skip first word, look for capitals
    for i, word in enumerate(words[1:], 1):
        clean = re.sub(r"[^\w]", "", word)
        if clean and clean[0].isupper() and clean.lower() not in PERSONAL_INDICATORS:
            return clean.lower()
    
    # Also check for "X is a" pattern
    match = re.search(r"(\w+) is (?:a|an) ", text, re.IGNORECASE)
    if match:
        name = match.group(1).lower()
        if name not in PERSONAL_INDICATORS and name not in {"this", "that", "it", "what", "there"}:
            return name
    
    return None


def _extract_attribute(text: str) -> Optional[str]:
    """Extract the attribute being asked about."""
    # Remove common prefixes
    for prefix in ["what is my", "what's my", "whats my", "tell me my", "what is", "who is"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    
    # Remove trailing punctuation
    text = re.sub(r'[?\.]$', '', text).strip()
    
    # Get first meaningful word(s)
    words = text.split()
    if words:
        # Check for compound attributes like "favorite color"
        if len(words) >= 2 and words[0] in {"favorite", "favourite"}:
            return f"{words[0]}_{words[1]}"
        return words[0].replace("'s", "").replace("s'", "")
    
    return None


def _extract_attr_value(text: str, is_personal: bool = False, entity_name: str = None) -> Tuple[Optional[str], Optional[str]]:
    """Extract attribute and value from a store statement."""
    text_lower = text.lower()
    
    # Pattern: "my X is Y"
    if is_personal:
        match = re.search(r"(?:my|i'm|im|i am) (\w+(?:\s+\w+)?) (?:is|=) (.+)", text, re.IGNORECASE)
        if match:
            attr = match.group(1).strip().replace(" ", "_").lower()
            val = match.group(2).strip()
            return attr, val
        
        # Pattern: "call me X" / "I'm X"
        match = re.search(r"(?:call me|i'm|im|i am) (\w+)", text, re.IGNORECASE)
        if match:
            return "name", match.group(1).strip()
    
    if entity_name:
        # Pattern: "X is a Y"
        match = re.search(rf"{entity_name} is (?:a|an)? ?(.+)", text, re.IGNORECASE)
        if match:
            return "role", match.group(1).strip()
        
        # Pattern: "X's Y is Z"
        match = re.search(rf"{entity_name}(?:'s|s) (\w+(?:\s+\w+)?) (?:is|=) (.+)", text, re.IGNORECASE)
        if match:
            attr = match.group(1).strip().replace(" ", "_").lower()
            val = match.group(2).strip()
            return attr, val
    
    # Generic: "X is Y"
    match = re.search(r"(\w+(?:\s+\w+)?)\s+(?:is|=)\s+(.+)", text, re.IGNORECASE)
    if match:
        attr = match.group(1).strip().replace(" ", "_").lower()
        val = match.group(2).strip()
        return attr, val
    
    return None, None


def _extract_fact(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract fact subject and value."""
    # Remove common prefixes
    for prefix in ["remember that", "remember", "note that"]:
        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
            break
    
    # Pattern: "X is Y"
    match = re.search(r"(.+?)\s+(?:is|means|=)\s+(.+)", text, re.IGNORECASE)
    if match:
        subject = match.group(1).strip().lower().replace(" ", "_")
        value = match.group(2).strip()
        return subject, value
    
    return None, None


def _extract_query_subject(text: str) -> Optional[str]:
    """Extract what is being queried."""
    # Remove common prefixes
    for prefix in ["what is", "what's", "whats", "tell me about", "tell me", "what is the", "what's the"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    
    # Remove trailing punctuation
    text = re.sub(r'[?\.]$', '', text).strip()
    
    return text.replace(" ", "_") if text else None
