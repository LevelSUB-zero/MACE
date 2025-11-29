import traceback
from mace.core import structures, deterministic, reflective_log
from mace.router import router_stage0
from mace.agents import math_agent, profile_agent, knowledge_agent, generic_agent
from mace.council import council_stub

# Agent Registry
AGENTS = {
    "math_agent": math_agent,
    "profile_agent": profile_agent,
    "knowledge_agent": knowledge_agent,
    "generic_agent": generic_agent
}

def execute(percept_text, intent="unknown", seed=None, log_enabled=True):
    """
    Main execution loop for Stage-0.
    """
    # 0. Seed Chaining for Determinism/Replayability
    # We derive a new seed from the current state + input, and reset counters.
    # This ensures that the log's random_seed (which is the new seed) 
    # fully determines the execution state (counters=0).
    import hashlib
    
    if seed is not None:
        # Replay mode: use provided seed
        next_seed = seed
    else:
        # Normal mode: derive seed
        current_seed = deterministic.get_seed() or "genesis_seed"
        # Mix in text and intent to ensure variation
        payload = f"{current_seed}:{percept_text}:{intent}".encode("utf-8")
        next_seed = hashlib.sha256(payload).hexdigest()
        
    deterministic.init_seed(next_seed)

    # 1. Build Percept
    percept = structures.create_percept(percept_text, intent=intent)
    
    # 2. Create Brainstate (Before)
    brainstate_before = structures.create_brainstate()
    
    # 3. Router
    router_decision = router_stage0.route(percept, brainstate_before)
    
    # Select primary agent
    primary_selection = router_decision["selected_agents"][0]
    agent_id = primary_selection["agent_id"]
    
    # 4. Execute Agent
    agent_module = AGENTS.get(agent_id, generic_agent)
    
    errors = []
    agent_outputs = []
    
    # Start capturing memory traces
    from mace.memory import semantic
    semantic.start_capture()
    
    try:
        output = agent_module.run(percept)
        agent_outputs.append(output)
    except Exception as e:
        # Handle Agent Failure (F4)
        err_msg = str(e)
        stack = traceback.format_exc()
        
        error_event = structures.create_error_event(
            context_id=percept["percept_id"],
            message=f"Agent {agent_id} failed: {err_msg}",
            origin={"module_id": "executor", "agent_id": agent_id, "module_version": "0.0.1"}
        )
        error_event["stack_summary"] = stack
        errors.append(error_event)
        
        # Fallback
        fallback_output = structures.create_agent_output(
            agent_id="generic_agent",
            text="One of my internal modules failed while processing this; here is a partial answer based on the remaining modules.",
            confidence=0.0
        )
        agent_outputs.append(fallback_output)
        output = fallback_output

    # Stop capturing
    captured_traces = semantic.stop_capture()
    memory_reads = captured_traces["reads"]
    memory_writes = captured_traces["writes"]
    
    # 4. Council
    vote = council_stub.evaluate(output)
    council_votes = [vote]
    
    # 5. Final Output Selection
    final_output = select_final_output(agent_outputs)
    
    brainstate_after = structures.create_brainstate()
    if errors:
        brainstate_after["last_error"] = errors[-1]

    # 6. Reflective Log
    # Note: In Stage-0 we don't track detailed memory reads/writes in the executor scope easily 
    # without a context manager or passing a tracker to agents. 
    # For now, we leave them empty in the log unless agents return them (which they don't in current signature).
    # Future improvement: Agents return (output, reads, writes).
    
    log_entry = structures.create_reflective_log_entry(
        percept=percept,
        router_decision=router_decision,
        council_votes=council_votes,
        final_output=final_output,
        brainstate_before=brainstate_before,
        brainstate_after=brainstate_after,
        errors=errors,
        memory_reads=memory_reads,
        memory_writes=memory_writes
    )
    
    if log_enabled:
        reflective_log.append_log(log_entry)
        
    # Telemetry
    # We calculate latency based on real time for ops metrics
    import time
    # Note: This violates D2 strictly but is necessary for 8.1 "avg_latency_ms"
    # We assume telemetry is external to the "Brain" logic.
    # For Stage-0, we'll just mock it or use a delta if we tracked start time.
    # But we didn't track start time.
    # Let's assume 100ms for now or add start_time capture at top.
    
    # Check approval
    approved = True
    if council_votes:
        approved = council_votes[0]["approve"]
        
    from mace.core import telemetry
    telemetry.update_apt(approved, 100) # Mock 100ms for now to avoid time.time() import issues/D2 violation
    
    return final_output, log_entry

def select_final_output(agent_outputs):
    """
    Select the best output from a list of agent outputs.
    Deterministic tie-breaking:
    1. Highest confidence
    2. Lowest lexicographical agent_id
    """
    if not agent_outputs:
        return {
            "text": "No agents produced output.",
            "confidence": 0.0,
            "speculative": False
        }
        
    # Sort by confidence (desc) then agent_id (asc)
    # We use a tuple (confidence, agent_id)
    # Python sort is stable.
    # To sort by confidence desc and agent_id asc:
    # We can sort by agent_id asc first, then confidence desc.
    
    sorted_outputs = sorted(agent_outputs, key=lambda x: x["agent_id"])
    sorted_outputs = sorted(sorted_outputs, key=lambda x: x["confidence"], reverse=True)
    
    best = sorted_outputs[0]
    
    return {
        "text": best["text"],
        "confidence": best["confidence"],
        "speculative": False
    }
