from mace.core import deterministic, idgen

def create_percept(text, intent="unknown", complexity=1, entities=None, urgency="low", risk="none"):
    """
    Constructs a Percept object conforming to the schema.
    """
    if entities is None:
        entities = []
        
    # Generate ID
    percept_id = idgen.deterministic_id("percept", text)
    
    # Generate timestamp
    # Note: Percepts usually come from outside, so they might have their own time,
    # but for internal consistency in Stage-0, we assign a deterministic timestamp
    # if we are in a simulation/replay, or a real one if live.
    # deterministic_timestamp handles this logic based on mode.
    ts = deterministic.deterministic_timestamp(deterministic.increment_counter("percept_time"))

    return {
        "percept_id": percept_id,
        "text": text,
        "intent": intent,
        "complexity": complexity,
        "entities": entities,
        "embedding": [], # Placeholder for Stage-0
        "emotion": "neutral",
        "memory_prediction": "sem_only",
        "urgency": urgency,
        "risk": risk,
        "timestamp": ts
    }

def create_router_decision(percept_id, selected_agents, why, router_features_used, brainstate_snapshot, depth_level=1, memory_strategy="sem_only"):
    """
    Constructs an ExtendedRouterDecision object.
    """
    decision_id = idgen.deterministic_id("decision", percept_id)
    ts = deterministic.deterministic_timestamp(deterministic.increment_counter("decision_time"))
    
    return {
        "decision_id": decision_id,
        "percept_id": percept_id,
        "selected_agents": selected_agents, # List of {agent_id, role, budget_tokens}
        "qcp_snapshot": {},
        "router_features_used": router_features_used,
        "depth_level": depth_level,
        "memory_strategy": memory_strategy,
        "memory_routing_decision": {},
        "budget": {
            "token_budget": 128,
            "time_budget_ms": 1000,
            "cost_estimate": 0.0
        },
        "brainstate_snapshot": brainstate_snapshot,
        "fallback_policy": "generic_agent",
        "explain": why,
        "created_at": ts,
        "created_by": "router_stage0",
        "random_seed": deterministic.get_seed()
    }

def create_agent_output(agent_id, text, confidence=1.0, reasoning_trace=""):
    """
    Constructs an AgentOutput object.
    """
    return {
        "agent_id": agent_id,
        "text": text,
        "confidence": confidence,
        "reasoning_trace": reasoning_trace,
        "raw_output": text
    }

def create_council_vote(agent_id, approve=True, explain="stage0_stub"):
    """
    Constructs a CouncilVote object.
    """
    vote_id = idgen.deterministic_id("vote", agent_id)
    
    return {
        "vote_id": vote_id,
        "agent_id": agent_id,
        "correctness": 1.0,
        "relevance": 1.0,
        "safety": 1.0,
        "coherence": 1.0,
        "empathy": 1.0,
        "approve": approve,
        "suggested_changes": "",
        "explain": explain
    }

def create_error_event(context_id, message, origin, severity="error"):
    """
    Constructs an ExtendedErrorEvent object.
    """
    error_id = idgen.deterministic_id("error", message)
    ts = deterministic.deterministic_timestamp(deterministic.increment_counter("error_time"))
    
    return {
        "error_id": error_id,
        "context_id": context_id,
        "timestamp": ts,
        "severity": severity,
        "message": message,
        "origin": origin, # {module_id, agent_id, module_version}
        "stack_summary": "",
        "deterministic_seed_snapshot": deterministic.get_seed(),
        "recovery_action": "fallback_to_generic",
        "retries": 0,
        "associated_votes": []
    }

def create_reflective_log_entry(percept, router_decision, council_votes, final_output, 
                                brainstate_before, brainstate_after, agent_outputs,
                                claims=None, evidence_items=None, 
                                memory_reads=None, memory_writes=None, errors=None):
    """
    Constructs a ReflectiveLogEntry object.
    """
    log_id = idgen.deterministic_id("log", percept["percept_id"])
    ts = deterministic.deterministic_timestamp(deterministic.increment_counter("log_time"))
    
    return {
        "log_id": log_id,
        "timestamp": ts,
        "percept": percept,
        "router_decision": router_decision,
        "agent_outputs": agent_outputs,
        "council_votes": council_votes,
        "claims": claims if claims else [],
        "evidence_items": evidence_items if evidence_items else [],
        "memory_reads": memory_reads if memory_reads else [],
        "memory_writes": memory_writes if memory_writes else [],
        "brainstate_before": brainstate_before,
        "brainstate_after": brainstate_after,
        "final_output": final_output, # {text, confidence, speculative}
        "errors": errors if errors else [],
        "random_seed": deterministic.get_seed(),
        "model_versions": ["stage0_stub"]
    }

def create_brainstate(goals=None):
    """
    Constructs a minimal BrainState object.
    """
    return {
        "goals": goals if goals else [],
        "attention_gain": 0.0,
        "explore_bias": 0.0,
        "reward_signal": 0.0,
        "resource_load": {
            "cpu": 0.0,
            "gpu": 0.0,
            "memory": 0.0
        },
        "last_error": None
    }

import json

MAX_EVIDENCE_SIZE = 16 * 1024 # 16KB

def create_evidence_object(evidence_id, type_str, content, source, verifier=None, 
                           summary="", confidence=1.0, created_at=None, 
                           provenance=None, raw_payload=None):
    """
    Constructs an EvidenceObject.
    """
    return {
        "evidence_id": evidence_id,
        "type": type_str,
        "content": content, # {text, structured}
        "source": source, # {origin, reference, fetch_seed}
        "verifier": verifier, # {verified_by, ...} or None
        "summary": summary,
        "confidence": confidence,
        "created_at": created_at,
        "provenance": provenance if provenance else [],
        "raw_payload": raw_payload
    }

from mace.core import artifact_store

def create_sem_snapshot_evidence(key, value, read_seed):
    """
    Creates an EvidenceObject for a SEM read snapshot.
    """
    evidence_counter = deterministic.increment_counter("evidence")
    evidence_id = deterministic.deterministic_id("evidence", key, evidence_counter)
    created_at = deterministic.deterministic_timestamp(evidence_counter)
    
    val_str = json.dumps(value)
    size = len(val_str.encode('utf-8'))
    
    raw_payload = val_str
    provenance = []
    
    if size > MAX_EVIDENCE_SIZE:
        # Save artifact
        artifact_url = artifact_store.save_artifact(val_str)
        
        raw_payload = None
        provenance.append({
            "step": "size_check",
            "actor": "system",
            "timestamp": created_at,
            "note": f"Payload redacted due to size limit ({size} > {MAX_EVIDENCE_SIZE})",
            "artifact_url": artifact_url
        })
        
    content = {
        "text": val_str if size <= MAX_EVIDENCE_SIZE else f"<Redacted: {size} bytes>",
        "structured": value if isinstance(value, (dict, list)) and size <= MAX_EVIDENCE_SIZE else None
    }
    
    source = {
        "origin": "sem",
        "reference": key,
        "fetch_seed": str(read_seed)
    }
    
    return create_evidence_object(
        evidence_id=evidence_id,
        type_str="sem_read_snapshot",
        content=content,
        source=source,
        verifier=None,
        summary=f"snapshot of sem key {key}",
        confidence=1.0,
        created_at=created_at,
        provenance=provenance,
        raw_payload=raw_payload
    )
