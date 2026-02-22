"""
Math Agent - Stage-0 Implementation

Solves simple mathematical operations.
Handles both symbolic ("2 + 2") and natural language ("what is 2 plus 2") inputs.
"""
import re
from mace.core import structures


# Map words to operators
OP_MAP = {
    "plus": "+",
    "add": "+",
    "added to": "+",
    "minus": "-",
    "subtract": "-",
    "times": "*",
    "multiplied by": "*",
    "divide": "/",
    "divided by": "/",
    "over": "/",
    "power": "**",
    "^": "**"
}


def _parse_math_expression(text: str) -> str:
    """
    Parse a natural language math query into a python expression.
    """
    text = text.lower().strip()
    
    # Remove common prefixes
    for prefix in ["what is", "calculate", "compute", "solve", "what's", "whats"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
            
    # Remove trailing '?'
    text = text.rstrip("?")
    
    # Replace word operators with symbols
    for word, op in OP_MAP.items():
        text = text.replace(word, op)
    
    # Allow only safe characters: digits, ., +, -, *, /, (, )
    # Remove everything else
    clean_expr = re.sub(r"[^0-9\.\+\-\*\/\(\)\s]", "", text)
    
    # Check if empty or just whitespace
    if not clean_expr.strip():
        raise ValueError("No valid math expression found")
        
    return clean_expr


def run(percept):
    """
    Execute math agent.
    """
    text = percept["text"]
    
    try:
        expr = _parse_math_expression(text)
        
        # Safe eval (still restricted to math specific subset)
        # In a real system, use a proper parser library like `ast` or `sympy`
        # For Stage-0, eval on sanitized string is acceptable if sanitized strictly
        
        # Verify safety again - no letters allowed
        if re.search(r"[a-zA-Z]", expr):
             # This might happen if 'e' is used for scientific notation, let's allow 'e' if followed by digits?
             # For now, simplistic approach.
             print(f"DEBUG: Math safety check failed for expr: '{expr}'")
             raise ValueError("Unsafe characters in expression")
             
        print(f"DEBUG: Math eval expr: '{expr}'")
        # Eval
        result = eval(expr, {"__builtins__": {}}, {})
        
        # Format result
        if isinstance(result, float) and result.is_integer():
            result = int(result)
            
        return structures.create_agent_output(
            agent_id="math_agent",
            text=str(result),
            confidence=1.0,
            reasoning_trace=f"Evaluated expression: {expr}"
        )
        
    except Exception as e:
        return structures.create_agent_output(
            agent_id="math_agent",
            text="I couldn't calculate that.",
            confidence=0.0,
            reasoning_trace=f"Math error: {str(e)}"
        )
