import json
from mace.memory import semantic
from mace.runtime import executor
from mace.core import canonical

def replay_log(log_entry):
    """
    Replay a session from a Reflective Log entry.
    """
    # 1. Extract seed
    # Stage-1 logs might have 'random_seed' or derived from 'immutable_subpayload' signature?
    # The executor uses 'random_seed' in log entry.
    seed = log_entry.get("random_seed")
    if not seed:
        return {"success": False, "error": "MISSING_SEED"}
        
    # 2. Extract evidence and build snapshot
    evidence_items = log_entry.get("evidence_items", [])
    snapshot = {}
    
    for ev in evidence_items:
        if ev["type"] == "sem_read_snapshot":
            key = ev["source"]["reference"]
            val = ev["content"]["structured"]
            if val is None:
                text_content = ev["content"]["text"]
                if text_content and not text_content.startswith("<Redacted"):
                    try:
                        val = json.loads(text_content)
                    except:
                        val = text_content
                elif text_content and text_content.startswith("<Redacted"):
                    return {"success": False, "error": "EVIDENCE_REDACTED", "details": f"Key {key} is redacted."}
            snapshot[key] = val
            
    # 3. Set replay store
    # We need to ensure semantic module has ReplaySEMStore
    # Assuming semantic.py has it (it was referenced in old replay.py)
    replay_store = semantic.ReplaySEMStore(snapshot)
    semantic.set_store(replay_store)
    
    try:
        # 4. Run executor
        percept_text = log_entry["percept"]["text"]
        intent = log_entry["percept"]["intent"]
        
        # Disable log writing during replay, but we need the log object returned
        final_output, new_log = executor.execute(percept_text, intent=intent, seed=seed, log_enabled=False)
        
        # 5. Verify Log ID (Proves Deterministic Execution)
        if new_log["log_id"] != log_entry["log_id"]:
            return {
                "success": False, 
                "error": "LOG_ID_MISMATCH", 
                "details": f"Expected {log_entry['log_id']}, got {new_log['log_id']}"
            }
            
        # 6. Verify Key Deterministic Outcomes
        # For Stage-1, we verify critical fields match rather than requiring perfect byte match
        
        # Final output text (the user-facing result)
        if log_entry["final_output"]["text"] != new_log["final_output"]["text"]:
            return {
                "success": False,
                "error": "OUTPUT_MISMATCH",
                "details": f"Expected '{log_entry['final_output']['text']}', got '{new_log['final_output']['text']}'"
            }
            
        # Router decision (which agent was selected)
        orig_agents = [a["agent_id"] for a in log_entry["router_decision"]["selected_agents"]]
        new_agents = [a["agent_id"] for a in new_log["router_decision"]["selected_agents"]]
        if orig_agents != new_agents:
            return {
                "success": False,
                "error": "ROUTING_MISMATCH",
                "details": f"Expected agents {orig_agents}, got {new_agents}"
            }
             
        return {"success": True}
        
    finally:
        semantic.set_store(semantic.LiveSEMStore())
