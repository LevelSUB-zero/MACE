import re
from mace.core import deterministic

def analyze_percept(percept):
    """
    Analyze a Percept and return a QCP snapshot.
    Stage-0 Stub: Uses deterministic regex mapping.
    
    Args:
        percept (dict): The Percept object (must contain 'content.text').
        
    Returns:
        dict: A qcp_snapshot object.
    """
    text = ""
    if percept and "text" in percept:
        text = percept["text"]
    
    text_lower = text.lower()
    
    # Default values
    intent_tags = ["general_conversation"]
    features = {}
    
    # Regex Mapping
    # 1. Math: "1 + 1", "5 * 5", "2 + (3)"
    # Allow digits, parens, decimals, spaces, and at least one operator
    if re.search(r"^\s*\d+\s*[\+\-\*\/\^]\s*\d+\s*$", text):
        intent_tags = ["math_operation"]
        features["math"] = True
        
    # 2. Profile: "my name is", "i like", "what is my", "my"
    elif re.search(r"\b(my name is|i like|i am|my favorite|what is my|my)\b", text_lower):
        intent_tags = ["profile_update"]
        features["profile"] = True
        
    # 3. Fact: "what is", "define"
    elif re.search(r"^(what is|define|who is)\b", text_lower):
        intent_tags = ["knowledge_query"]
        features["fact"] = True
        
    # Construct snapshot
    snapshot = {
        "intent_tags": intent_tags,
        "features": features,
        "depth_level": 1,
        "urgency": "medium",
        "risk": "low",
        "qcp_version": "0.0.2-stub",
        "random_seed": deterministic.get_seed()
    }
    
    return snapshot
