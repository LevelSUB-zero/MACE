import json
from mace.core import deterministic
from mace.runtime import executor

# Fields to validate for exact match
VALIDATE_FIELDS = [
    "router_decision",
    "selected_agents",
    "agent_outputs",
    "sem_reads",
    "sem_writes",
    "final_output",
    "council_votes",
    "claims",
    "evidence_items",
    "brainstate_before",
    "brainstate_after"
]

def replay_log(log_entry):
    """
    Replay a single log entry and verify determinism.
    Raises RuntimeError if mismatch found.
    """
    # 1. Set Mode
    deterministic.set_mode("DETERMINISTIC")
    
    # 2. Extract Context
    percept = log_entry["percept"]
    text = percept["text"]
    intent = percept["intent"]
    seed = log_entry["random_seed"]
    
    # 3. Re-Execute
    # Note: We pass the seed from the log, which ensures the executor 
    # initializes with the exact same seed as the original run.
    # We disable logging to avoid polluting the log file during replay.
    
    # Inject memory snapshot if present
    from mace.memory import semantic
    if "memory_reads" in log_entry:
        semantic.set_replay_snapshot(log_entry["memory_reads"])
    
    try:
        _, replay_log_entry = executor.execute(text, intent=intent, seed=seed, log_enabled=False)
    finally:
        # Clear snapshot
        semantic.set_replay_snapshot(None)
    
    # 4. Compare
    compare_logs(log_entry, replay_log_entry)
    
    return True 

def compare_logs(original, replay):
    """
    Compare two log entries field by field.
    """
    mismatches = []
    
    for field in VALIDATE_FIELDS:
        val_orig = original.get(field)
        val_replay = replay.get(field)
        
        # Deep comparison (JSON equality)
        # We assume standard python dict equality works for these structures
        if val_orig != val_replay:
            msg = f"Field '{field}' mismatch:\nOriginal: {val_orig}\nReplay:   {val_replay}"
            mismatches.append(msg)
            
    if mismatches:
        with open("replay_debug.txt", "w") as f:
            f.write("\n".join(mismatches))
        raise RuntimeError("REPLAY_MISMATCH:\n" + "\n".join(mismatches))
    
    return True
