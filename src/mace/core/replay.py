import json
from mace.memory import semantic
from mace.runtime import executor

def replay_log(log_entry):
    """
    Replay a session from a Reflective Log entry.
    
    Args:
        log_entry (dict): The log entry to replay.
        
    Returns:
        dict: {"success": bool, "error": str, "details": str}
    """
    # 1. Extract seed
    seed = log_entry.get("random_seed")
    if not seed:
        return {"success": False, "error": "MISSING_SEED"}
        
    # 2. Extract evidence and build snapshot
    evidence_items = log_entry.get("evidence_items", [])
    snapshot = {}
    
    for ev in evidence_items:
        if ev["type"] == "sem_read_snapshot":
            key = ev["source"]["reference"]
            
            # Extract value
            # Priority: structured -> text (parsed)
            val = ev["content"]["structured"]
            
            if val is None:
                text_content = ev["content"]["text"]
                if text_content and not text_content.startswith("<Redacted"):
                    try:
                        val = json.loads(text_content)
                    except:
                        # Should not happen if it was valid JSON
                        val = text_content
                elif text_content and text_content.startswith("<Redacted"):
                    return {"success": False, "error": "EVIDENCE_REDACTED", "details": f"Key {key} is redacted."}
            
            snapshot[key] = val
            
    # 3. Set replay store (Sandbox)
    replay_store = semantic.ReplaySEMStore(snapshot)
    semantic.set_store(replay_store)
    
    try:
        # 4. Run executor
        percept_text = log_entry["percept"]["text"]
        intent = log_entry["percept"]["intent"]
        
        # Disable log writing during replay
        final_output, new_log = executor.execute(percept_text, intent=intent, seed=seed, log_enabled=False)
        
        # 5. Compare
        # 5. Compare
        
        def _deep_compare(obj1, obj2, field_name):
            s1 = json.dumps(obj1, sort_keys=True)
            s2 = json.dumps(obj2, sort_keys=True)
            if s1 != s2:
                # Truncate diff if too long
                diff = f"Expected {s1}, got {s2}"
                if len(diff) > 1000:
                    diff = diff[:1000] + "... (truncated)"
                return False, f"{field_name}_MISMATCH: {diff}"
            return True, None

        # Compare Final Output
        match, err = _deep_compare(log_entry["final_output"], final_output, "FINAL_OUTPUT")
        if not match:
            return {"success": False, "error": "OUTPUT_MISMATCH", "details": err}

        # Compare Router Decision
        # We compare the whole object for strictness
        match, err = _deep_compare(log_entry["router_decision"], new_log["router_decision"], "ROUTER_DECISION")
        if not match:
             return {"success": False, "error": "ROUTING_MISMATCH", "details": err}
            
        # Compare Memory Reads
        match, err = _deep_compare(log_entry["memory_reads"], new_log["memory_reads"], "MEMORY_READS")
        if not match:
            return {"success": False, "error": "MEMORY_READS_MISMATCH", "details": err}
            
        # Compare Memory Writes
        match, err = _deep_compare(log_entry["memory_writes"], new_log["memory_writes"], "MEMORY_WRITES")
        if not match:
            return {"success": False, "error": "MEMORY_WRITES_MISMATCH", "details": err}
            
        # Compare Errors
        match, err = _deep_compare(log_entry["errors"], new_log["errors"], "ERRORS")
        if not match:
             return {"success": False, "error": "ERROR_MISMATCH", "details": err}
             
        # Compare Council Votes
        match, err = _deep_compare(log_entry["council_votes"], new_log["council_votes"], "COUNCIL_VOTES")
        if not match:
             return {"success": False, "error": "COUNCIL_VOTE_MISMATCH", "details": err}
                
        # Compare Agent Outputs
        match, err = _deep_compare(log_entry["agent_outputs"], new_log["agent_outputs"], "AGENT_OUTPUTS")
        if not match:
             return {"success": False, "error": "AGENT_OUTPUT_MISMATCH", "details": err}
            
        return {"success": True}
        
    finally:
        # Cleanup: Restore Live Store
        semantic.set_store(semantic.LiveSEMStore())
