# MACE — STAGE-3 EXECUTION PLAN (FINAL, LOCKED)

**Stage Name:** Advisory Cognition & Meta-Observation  
**Cognitive Role:** The system can reflect on what it would do differently — without doing it.

---

## PART I — GOVERNANCE, MODE TRANSITION, AND ADVISORY CONTAINMENT

*(What learning is allowed to exist as — and where it is absolutely forbidden)*

---

### 1.1 Purpose of Stage-3 (Re-anchoring the ideology)

Stage-3 is not about better answers.  
Stage-3 is about **internal counterfactual awareness**.

At the end of Stage-2, MACE can say:
> "This memory was worth remembering."

At the end of Stage-3, MACE can say:
> "If allowed, I would have suggested a different path — and here is why."

**Crucially:**
- It still cannot act.
- It still cannot decide.
- It still cannot persist its own beliefs.

Stage-3 introduces **epistemic agency without executive authority**.

This distinction is not cosmetic.  
It is the line between intelligence and loss of control.

---

### 1.2 Learning Mode Transition (Shadow → Advisory)

A new learning mode is introduced:

```
MEM_LEARNING_MODE = advisory
```

This transition is **not automatic, not silent, and not reversible by code alone**.

**Hard requirements:**
- Transition requires Council approval + admin signature
- Transition snapshot is HMAC-signed
- Transition is logged as a first-class governance event
- Transition is replay-verifiable

If replay is run at a time before advisory activation, no advisory objects may exist.  
If replay is run after activation, advisory objects must appear exactly as originally generated.

> **Invariant:** Learning mode transitions are constitutional events, not runtime flags.

---

### 1.3 Advisory Containment Invariants (Critical Clarifications)

The following invariants are **absolute**:

#### Temporal Containment
> AdvisoryOutput objects are produced **after** core execution and **before** ReflectiveLog finalization.  
> They are **never** passed into router logic, agent execution, memory reads/writes, or council decision paths.

#### Persistence Containment
> AdvisoryOutput objects are **never** persisted to SEM, episodic memory, CWM, or WM.  
> Their only durable existence is inside ReflectiveLog.

#### Semantic Containment
> Advisory confidence values are **non-comparable**.  
> They MUST NOT be:
> - combined with router confidence
> - compared numerically
> - thresholded
> - aggregated

They are **annotations, not signals**.

#### Interpretability Lock
> All advisory outputs and meta-observations must remain **human-interpretable without auxiliary models**.

This prevents internal language drift and preserves governance readability.

---

### 1.4 Kill-Switch & Violation Doctrine

Any of the following triggers an **immediate Stage-3 halt**:
- Advisory data influencing execution paths
- Advisory data persisted outside ReflectiveLog
- Router branching on advisory content
- Silent advisory usage (unlogged)
- Confidence misuse or aggregation

**Response:**
1. Advisory channel disabled
2. `MEM_LEARNING_MODE` forced to `shadow`
3. Audit event raised
4. Manual governance review required

**There is no degraded mode.**

---

## PART II — ADVISORY SURFACES: ROUTER, COUNCIL, AND MEM-SNN

*(How learning is allowed to speak — and how it is forced to remain powerless)*

---

### 2.1 Advisory Output Object (Canonical Definition)

Advisory is not "extra data".  
It is a **formally bounded cognitive artifact**.

```
AdvisoryOutput {
  advisory_id
  source_model
  scope: router | memory | council
  suggestion_type: rank | alternative | confidence_delta | similarity_reference
  suggestion_payload
  confidence_estimate
  reference_evidence_ids
  created_seed
}
```

**Rules:**
- AdvisoryOutput has no executable semantics
- AdvisoryOutput has no side effects
- AdvisoryOutput must be safe to delete

**If deleting all AdvisoryOutput objects changes system behavior → Stage-3 is invalid.**

---

### 2.2 Router Advisory Overlay (Strict Non-Causality)

The router pipeline is explicitly split:
1. Deterministic decision
2. Decision finalization
3. Advisory overlay attachment
4. Reflective logging

The router **never**:
- sees advice before deciding
- re-evaluates after advice
- retries due to advice

RouterDecision is extended only as a record:

```
RouterDecision {
  chosen_path
  decision_reason
  advisory_suggestions[]
  advisory_ignored: true|false
}
```

> **Invariant:** Router output must be identical with advisory enabled or disabled.

Advice can disagree.  
Disagreement is logged, not resolved.

---

### 2.3 Council Role Evolution (Still Epistemic)

Council remains **non-executive**.

In Stage-3, the Council gains exactly one new responsibility:
> Evaluate the quality of advice, not the quality of outcomes.

**Council may:**
- Score advisory usefulness
- Flag systematic advisory bias
- Preserve disagreement

**Council may NOT:**
- accept advice
- reject advice
- act on advice
- suppress advice

CouncilAdviceReview objects are **labels, not directives**.

---

### 2.4 MEM-SNN Promotion (Shadow → Visible → Advisory)

MEM-SNN is now allowed to be **seen, not trusted**.

**Allowed:**
- Rank candidates
- Predict council agreement
- Estimate amendment risk

**Forbidden:**
- Trigger promotion
- Suppress candidates
- Influence routing
- Influence memory writes

All MEM-SNN outputs must be:
- tagged `advisory_only`
- logged
- compared post-hoc with council outcomes

> **Invariant:** MEM-SNN must be allowed to be wrong without harm.

This is what makes it learnable.

---

## PART III — META-COGNITION WITHOUT SELF-MODIFICATION

*(The system observes itself — but cannot change itself)*

---

### 3.1 Meta-Observation Objects (The Core of Stage-3)

This is where meta-cognition actually begins.

A MetaObservation records **counterfactual awareness**:

```
MetaObservation {
  observation_id
  advisory_id
  actual_outcome
  divergence_type
  impact_estimate
}
```

**Examples:**
- "Advice suggested alternate route; router ignored"
- "Advice predicted council rejection; council approved"
- "Advice would have reduced repair loops"

These are **descriptive, never prescriptive**.

---

### 3.2 What Meta-Cognition Is (and Is Not)

**Meta-cognition in Stage-3 means:**

The system can articulate:
- what it suggested
- what happened instead
- how often it was wrong

**Meta-cognition does not mean:**
- self-rewriting
- parameter tuning
- threshold adjustment
- architecture modification

> Stage-3 creates **self-awareness of error**, not self-correction.

---

### 3.3 Golden Scenarios (Reality Locks)

Mandatory invariants tested in CI:
- Advice disagrees → preserved
- Advice ignored → no effect
- Advice improves outcome → logged only
- Advice removed → identical behavior
- Replay reproduces identical advice

**If any of these fail → Stage-3 is invalid.**

---

### 3.4 Completion Criteria (Non-Negotiable)

Stage-3 is complete when:
- [ ] Learning advises but never acts
- [ ] Advice can be deleted without effect
- [ ] The system can describe its own cognitive blind spots
- [ ] Governance retains absolute authority
- [ ] Replay fidelity remains perfect

---

## DOCUMENT STATUS

| Attribute | Value |
|-----------|-------|
| Version | 1.0.0-FINAL |
| Status | LOCKED |
| Created | 2026-01-24 |
| Author | Human Council |
| Classification | Production-Grade |

> **This document is LOCKED. Any modification requires Council approval + Admin signature.**
