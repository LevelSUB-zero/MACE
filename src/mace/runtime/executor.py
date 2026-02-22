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
from mace.memory.wm import WorkingMemory
from mace.memory.cwm import ContextualWorkingMemory
from mace.memory.episodic import EpisodicMemory
from mace.brainstate import persistence as bs_persistence

from mace.governance import killswitch
from mace.config import schema_validator

# Validate schema lock at module load (fail fast on drift)
_schema_validated = False

def _ensure_schema_valid():
    global _schema_validated
    if not _schema_validated:
        schema_validator.validate_all()
        _schema_validated = True

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
    # 0. Schema validation (fail fast on config drift)
    _ensure_schema_valid()
    
    # 0.5. Kill-switch check
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

    # 1.5 NLU Parsing
    parsed_entities = {}
    parsed_complexity = 1
    # Only run NLU if intent wasn't explicitly provided (e.g. by tests)
    if intent == "unknown":
        from mace.nlu.ollama_nlu import parse as nlu_parse
        from mace.core.intent_parser import parse_intent, IntentType
        
        nlu_result = nlu_parse(percept_text)
        intent = nlu_result.get("root_intent", "unknown")
        parsed_entities = nlu_result.get("entities", {})
        
        # Map string complexity to a numeric representation if needed
        complexity_str = nlu_result.get("complexity", "atomic")
        comp_map = {"atomic": 1, "conditional": 2, "compound": 3, "update": 2, "meta": 3, "reference_heavy": 3}
        parsed_complexity = comp_map.get(complexity_str, 1)

        # Fallback to legacy parser for tests without Ollama
        if nlu_result.get("_source", "") != "ollama" or intent == "unknown":
            legacy_parsed = parse_intent(percept_text)
            
            # Map legacy intent to new string intent if nlu also failed or didn't provide a granular intent
            legacy_map = {
                IntentType.MATH: "math",
                IntentType.STORE_USER_ATTR: "profile_store",
                IntentType.RECALL_USER_ATTR: "profile_recall",
                IntentType.STORE_ENTITY_ATTR: "contact_store",
                IntentType.RECALL_ENTITY_ATTR: "contact_recall",
                IntentType.TEACH_FACT: "fact_teach",
                IntentType.QUERY_FACT: "history_search",
                IntentType.GREETING: "greeting",
                IntentType.THANKS: "thanks",
                IntentType.HELP: "help",
            }
            mapped_intent = legacy_map.get(legacy_parsed["intent"], "unknown")
            if mapped_intent != "unknown" and intent == "unknown":
                intent = mapped_intent
            
            # Populate missing entities from legacy parser
            if not parsed_entities:
                if legacy_parsed.get("attribute"):
                    parsed_entities["attribute"] = legacy_parsed["attribute"]
                    # Legacy knowledge_agent expects "topic" if it's a fact query/teach but "attribute" is fine too, 
                    # as we handled both via `entities.get("attribute") or entities.get("topic")`
                if legacy_parsed.get("value"):
                    parsed_entities["value"] = legacy_parsed["value"]
                if legacy_parsed.get("subject") and legacy_parsed["subject"] != "user":
                    parsed_entities["person"] = legacy_parsed["subject"]

    # 2. Build Percept
    percept = structures.create_percept(
        percept_text, 
        intent=intent, 
        complexity=parsed_complexity, 
        entities=parsed_entities
    )
    
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
    
    # 4. Execute Agent (with timeout enforcement per Rule F4)
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
    from mace.config import config_loader
    
    agent_module = AGENTS.get(agent_id, generic_agent)
    metrics.increment("agent_executions_total")
    
    errors = []
    agent_outputs = []
    degraded_agents = []  # Track agents that failed this request
    
    # Start capturing memory traces
    semantic.start_capture()
    
    # Get timeout from config (default 30s)
    timeout_ms = config_loader.get_agent_timeout_ms()
    timeout_sec = timeout_ms / 1000.0
    
    def _run_agent():
        return agent_module.run(percept)
    
    try:
        print(f"DEBUG: Running agent {agent_id} with percept {percept['text']} (timeout: {timeout_sec}s)")
        
        # Execute with timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_agent)
            output = future.result(timeout=timeout_sec)
            
        print(f"DEBUG: Agent output: {output}")
        agent_outputs.append(output)
        
    except FuturesTimeout:
        # F4: Agent timeout - mark degraded and fallback
        err_msg = "AGENT_TIMEOUT"
        degraded_agents.append(agent_id)
        
        error_event = structures.create_error_event(
            context_id=percept["percept_id"],
            message=f"Agent {agent_id} timed out after {timeout_sec}s",
            origin={"module_id": "executor", "agent_id": agent_id, "module_version": "1.0.0"},
            severity="warning"
        )
        errors.append(error_event)
        
        # Fallback to generic_agent
        fallback_msg = f"My {agent_id.replace('_', ' ')} module timed out; here is a partial answer based on remaining modules."
        fallback_output = structures.create_agent_output(
            agent_id="generic_agent",
            text=fallback_msg,
            confidence=0.0,
            reasoning_trace=f"Fallback triggered due to {agent_id} timeout."
        )
        agent_outputs.append(fallback_output)
        output = fallback_output
        
    except Exception as e:
        # F4: Agent crash - mark degraded and fallback
        err_msg = str(e)
        stack = traceback.format_exc()
        degraded_agents.append(agent_id)
        
        error_event = structures.create_error_event(
            context_id=percept["percept_id"],
            message=f"Agent {agent_id} failed: {err_msg}",
            origin={"module_id": "executor", "agent_id": agent_id, "module_version": "1.0.0"},
            severity="error"
        )
        error_event["stack_summary"] = stack
        errors.append(error_event)
        
        # Fallback (no retries per Stage-0 spec)
        fallback_msg = "One of my internal modules failed while processing this."
        fallback_output = structures.create_agent_output(
            agent_id="generic_agent",
            text=fallback_msg,
            confidence=0.0,
            reasoning_trace="Fallback triggered due to agent crash."
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
    
    # 9. Record interaction to Episodic Memory
    try:
        episodic = EpisodicMemory(job_seed=next_seed)
        episodic.record_interaction(
            percept_text=percept_text,
            response_text=final_output["text"],
            agent_id=agent_id,
            job_seed=next_seed,
            metadata={
                "confidence": final_output["confidence"],
                "router_explain": router_decision.get("explain", ""),
                "had_errors": len(errors) > 0
            }
        )
    except Exception as e:
        # Episodic recording failure should not break execution
        pass
        
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
