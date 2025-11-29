from mace.core import structures

def run(percept):
    """
    Math Agent: Solves simple binary operations.
    Input: "2 + 2"
    Output: "4"
    """
    text = percept["text"]
    try:
        # Very simple eval for Stage-0 (safe because regex restricted input)
        # In production, use a proper parser.
        # Regex was: ^\s*\d+\s*([+\-*/^])\s*\d+\s*$
        # Replace ^ with ** for python
        expr = text.replace("^", "**")
        result = eval(expr)
        
        return structures.create_agent_output(
            agent_id="math_agent",
            text=str(result),
            confidence=1.0,
            reasoning_trace=f"Evaluated expression: {expr}"
        )
    except Exception as e:
        # Should be caught by executor, but good to have local handling
        raise e
