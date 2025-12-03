import traceback
import json
import datetime
from mace.core import structures, deterministic, canonical
from mace.router import stage1_router
from mace.brainstate import brainstate
from mace.reflective import writer as reflective_writer
from mace.council import stub as council_stub
from mace.agents import math_agent, profile_agent, knowledge_agent, generic_agent
from mace.ops import metrics
from mace.memory import semantic
from mace.brainstate import persistence as bs_persistence

from mace.governance import killswitch

# Agent Registry
AGENTS = {
    "math_agent": math_agent,
    "profile_agent": profile_agent,
    "knowledge_agent": knowledge_agent,
    "generic_agent": generic_agent
}

def execute(percept_text, intent="unknown", seed=None, log_enabled=True):
    """
    Main execution loop for Stage-1.
    """
    # 0. Kill-switch check
    if killswitch.is_active():
        status = killswitch.get_status()
        raise RuntimeError(f"KILL_SWITCH_ACTIVE: {status.get('reason', 'UNKNOWN')} (activated by {status.get('activated_by', 'unknown')})")
    
    # 1. Seed Chaining
    import hashlib
    
    if seed is not None:
        next_seed = seed
    else:
        current_seed = deterministic.get_seed() or "genesis_seed"
        payload = f"{current_seed}:{percept_text}:{intent}".encode("utf-8")
        next_seed = hashlib.sha256(payload).hexdigest()
        
    deterministic.init_seed(next_seed)

    # 1. Build Percept
    percept = structures.create_percept(percept_text, intent=intent)
    
    # 2. Load or Create Brainstate
    # Try to load existing state first
    bs_before = bs_persistence.load_latest_snapshot(next_seed)
    if bs_before is None:
        # No existing state, create fresh
        bs_before = brainstate.create_snapshot(next_seed)
    
    # 3. Router
    # We pass available agents metadata (mocked for now or loaded from SelfRep)
    available_agents = [
        {"module_id": "math_agent", "capabilities": ["math", "calc"]},
        {"module_id": "profile_agent", "capabilities": ["profile", "user"]},
        {"module_id": "knowledge_agent", "capabilities": ["knowledge", "fact"]},
        {"module_id": "generic_agent", "capabilities": ["chat"]}
    ]
    
    router_decision = stage1_router.route(percept, bs_before, available_agents)
    
    # Select primary agent
    primary_selection = router_decision["selected_agents"][0]
    agent_id = primary_selection["agent_id"]
    
    # 4. Execute Agent
    agent_module = AGENTS.get(agent_id, generic_agent)
    metrics.increment("agent_executions_total")
    
    errors = []
    agent_outputs = []
    
    # Start capturing memory traces
    semantic.start_capture()
    
    try:
        print(f"DEBUG: Running agent {agent_id} with percept {percept['text']}")
        output = agent_module.run(percept)
        print(f"DEBUG: Agent output: {output}")
        agent_outputs.append(output)
    except Exception as e:
        # Handle Agent Failure
        err_msg = str(e)
        stack = traceback.format_exc()
        
        severity = "error"
        if "TIMEOUT" in err_msg:
            err_msg = "AGENT_TIMEOUT"
            severity = "warning"
        
        error_event = structures.create_error_event(
            context_id=percept["percept_id"],
            message=f"Agent {agent_id} failed: {err_msg}",
            origin={"module_id": "executor", "agent_id": agent_id, "module_version": "1.0.0"},
            severity=severity
        )
        error_event["stack_summary"] = stack
        errors.append(error_event)
        
        # Fallback
        fallback_msg = "One of my internal modules failed."
        fallback_output = structures.create_agent_output(
            agent_id="generic_agent",
            text=fallback_msg,
            confidence=0.0,
            reasoning_trace="Fallback triggered."
        )
        agent_outputs.append(fallback_output)
        output = fallback_output

    # Stop capturing
    captured_traces = semantic.stop_capture()
    memory_reads = captured_traces["reads"]
    memory_writes = captured_traces["writes"]
    
    # Process Evidence
    evidence_items = []
    for key, read_info in memory_reads.items():
        if not read_info["exists"]:
            continue
        value = read_info["value"]
        read_seed = deterministic.get_seed()
        evidence = structures.create_sem_snapshot_evidence(key, value, read_seed)
        evidence_items.append(evidence)
    
    # 5. Council
    vote = council_stub.evaluate(output)
    council_votes = [vote]
    
    # 6. Final Output Selection
    final_output = select_final_output(agent_outputs)
    
    # 7. BrainState Update (Tick)
    # We tick the brainstate to advance time/decay
    brainstate.tick(bs_before)
    bs_after = bs_before # In-place update
    
    if errors:
        bs_after["last_error"] = errors[-1]

    # 8. Reflective Log
    # We need to ensure log_id is deterministic
    ts = deterministic.deterministic_timestamp(deterministic.increment_counter("executor_log_time"))
    log_payload = {
        "percept_id": percept["percept_id"],
        "timestamp": ts
    }
    log_id = deterministic.deterministic_id("reflective_log", canonical.canonical_json_serialize(log_payload))
    
    log_entry = structures.create_reflective_log_entry(
        percept=percept,
        router_decision=router_decision,
        council_votes=council_votes,
        final_output=final_output,
        brainstate_before=bs_before, # Note: this is actually mutated, ideally we should have deepcopied before
        brainstate_after=bs_after,
        agent_outputs=agent_outputs,
        errors=errors,
        memory_reads=list(memory_reads.keys()),
        memory_writes=memory_writes,
        evidence_items=evidence_items
    )
    log_entry["log_id"] = log_id
    
    if log_enabled:
        reflective_writer.write_log(log_entry)
        metrics.increment("reflective_logs_written_total")
        metrics.save()
    
    # Save updated BrainState for next execution
    bs_persistence.save_snapshot(bs_after)
        
    return final_output, log_entry

def select_final_output(agent_outputs):
    """
    Select the best output.
    """
    if not agent_outputs:
        return {
            "text": "No agents produced output.",
            "confidence": 0.0,
            "speculative": False
        }
    
    sorted_outputs = sorted(agent_outputs, key=lambda x: x["agent_id"])
    sorted_outputs = sorted(sorted_outputs, key=lambda x: x["confidence"], reverse=True)
    
    best = sorted_outputs[0]
    
    return {
        "text": best["text"],
        "confidence": best["confidence"],
        "speculative": False
    }
