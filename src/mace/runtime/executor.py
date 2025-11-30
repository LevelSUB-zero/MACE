import traceback
import json
from mace.core import structures, deterministic, reflective_log, qcp, router
from mace.agents import math_agent, profile_agent, knowledge_agent, generic_agent
from mace.council import council_stub
from mace.ops import metrics

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
    
    # 3. QCP Analysis
    qcp_snapshot = qcp.analyze_percept(percept)
    
    # 4. Router
    router_decision = router.route_percept(percept, qcp_snapshot)
    
    # Select primary agent
    primary_selection = router_decision["selected_agents"][0]
    agent_id = primary_selection["agent_id"]
    
    # 5. Execute Agent
    agent_module = AGENTS.get(agent_id, generic_agent)
    metrics.increment("agent_executions_total")
    
    errors = []
    agent_outputs = []
    
    # Start capturing memory traces
    from mace.memory import semantic
    semantic.start_capture()
    
    try:
        print(f"DEBUG: Running agent {agent_id} with percept {percept['text']}")
        output = agent_module.run(percept)
        print(f"DEBUG: Agent output: {output}")
        agent_outputs.append(output)
    except Exception as e:
        # Handle Agent Failure (F4)
        err_msg = str(e)
        stack = traceback.format_exc()
        
        # Check for specific failure types (simulated)
        severity = "error"
        if "TIMEOUT" in err_msg:
            # Simulated timeout
            err_msg = "AGENT_TIMEOUT"
            severity = "warning"
        
        error_event = structures.create_error_event(
            context_id=percept["percept_id"],
            message=f"Agent {agent_id} failed: {err_msg}",
            origin={"module_id": "executor", "agent_id": agent_id, "module_version": "0.0.1"},
            severity=severity
        )
        error_event["stack_summary"] = stack
        errors.append(error_event)
        
        # Fallback
        fallback_msg = "One of my internal modules failed while processing this; here is a partial answer based on the remaining modules."
        if "TIMEOUT" in err_msg:
             fallback_msg = "One of my internal modules timed out while trying to fetch the answer. I’ll try a fallback."
             
        fallback_output = structures.create_agent_output(
            agent_id="generic_agent",
            text=fallback_msg,
            confidence=0.0,
            reasoning_trace="Fallback triggered due to agent failure."
        )
        agent_outputs.append(fallback_output)
        output = fallback_output

    # Stop capturing
    captured_traces = semantic.stop_capture()
    memory_reads = captured_traces["reads"] # Dict {key: value}
    memory_writes = captured_traces["writes"] # List [key]
    
    # Process Evidence Snapshots
    evidence_items = []
    for key, read_info in memory_reads.items():
        # read_info is {"value": val, "exists": bool}
        if not read_info["exists"]:
            continue # Skip evidence for misses (replay will see missing key and infer miss)
            
        value = read_info["value"]
        
        # Create snapshot
        # We use the current seed as fetch_seed proxy for now
        read_seed = deterministic.get_seed()
        evidence = structures.create_sem_snapshot_evidence(key, value, read_seed)
        evidence_items.append(evidence)
    
    # 6. Council
    vote = council_stub.evaluate(output)
    council_votes = [vote]
    
    # 7. Final Output Selection
    final_output = select_final_output(agent_outputs)
    
    brainstate_after = structures.create_brainstate()
    if errors:
        brainstate_after["last_error"] = errors[-1]

    # 8. Reflective Log
    log_entry = structures.create_reflective_log_entry(
        percept=percept,
        router_decision=router_decision,
        council_votes=council_votes,
        final_output=final_output,
        brainstate_before=brainstate_before,
        brainstate_after=brainstate_after,
        agent_outputs=agent_outputs,
        errors=errors,
        memory_reads=list(memory_reads.keys()),
        memory_writes=memory_writes,
        evidence_items=evidence_items
    )
    
    if log_enabled:
        reflective_log.append_log(log_entry)
        metrics.increment("reflective_logs_written_total")
        metrics.save()
        
    if errors:
        metrics.increment("errors_total", len(errors))
        
    # Telemetry
    import time
    # Check approval
    approved = True
    if council_votes:
        approved = council_votes[0]["approve"]
        
    from mace.core import telemetry
    telemetry.update_apt(approved, 100) 
    
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
    

