# STAGE-0 RULEBOOK — MACE v0.0.2

## Scope of Stage-0
Only Semantic Memory (SEM) is “real” memory.
No episodic, no reflective, no long council loops yet.
Router is a dumb but deterministic stub (rule-based).
Goal of Stage-0 = predictable behavior, not “smartest mind”.

## 1. Determinism Rules (CRITICAL)

**Rule D1 — Deterministic Seed**
- The system must be initialized with a seed (integer or string).
- All random operations must derive from this seed.
- Global `_seed` must be stored in `core.deterministic`.

**Rule D2 — Deterministic Timestamp**
- System must NOT access system clock (time.time(), datetime.now()).
- Timestamp = ISO8601 derived from HMAC_SHA256(seed || counter).
- This ensures replayability of time-dependent logic.

**Rule D3 — Deterministic IDs**
- All IDs (percept_id, memory_id, vote_id, etc.) must be generated via:
  `HMAC_SHA256(seed || namespace || payload || counter)`
- Hex digest format.

## 2. Semantic Memory (SEM) — canonical_key rules

**Objective:**
Every stable fact must be stored under a canonical_key so we don’t duplicate or clash.

### 2.1 Canonical Key Format

**Rule S1 — Structure**
`<scope>/<entity_type>/<entity_id>/<attribute>`
Regex: `^[a-z0-9_\/]+$`

**Rule S2 — Allowed character set**
- Lowercase letters a–z
- Digits 0–9
- Underscore _ and forward slash /
- No spaces, no caps, no special chars.

**Rule S3 — Entity & attribute naming**
- `entity_type` is singular, snake_case
- `attribute` is also snake_case

**Rule S4 — Synonym handling**
SEM must not store synonyms as separate canonical keys. Map to one canonical key.

**Rule S5 — Versioning**
Stage-0: we support current state only.
PUT canonical_key = value always overwrites.

### 2.2 SEM-only Memory Semantics

**Rule S6 — SEM stores only stable-ish facts**
No raw chat logs, no full conversations.

**Rule S7 — SEM read contracts**
Given a canonical_key, SEM returns:
```json
{
  "exists": true/false,
  "value": <any JSON-serializable>,
  "last_updated": <timestamp>
}
```

**Rule S8 — Overwrite policy**
Last validated write wins.

**Rule S9 — No Inference on Miss**
If key doesn’t exist → exists=false.
System must not hallucinate a value.

## 3. Failure Cases & Deterministic Responses

**F1 — SEM miss**
Reply: “I don’t have this information stored yet.”

**F2 — Conflict in SEM**
Choose value with latest last_updated timestamp.

**F3 — No agent available**
Fallback: `generic_agent`.
Error: “I currently don’t have a module for this type of request.”

**F4 — Agent failure**
Mark degraded. Fallback to `generic_agent`.
Reply: “One of my internal modules failed while processing this; here is a partial answer based on the remaining modules.”

**F5 — SEM write failure**
Reply: “I tried to store this, but my memory backend failed. I may not remember this next time.”

## 4. Router Placeholder Rules (Stage-0 Stub)

**R1 — Math detection**
Regex: `^\s*\d+\s*([+\-*/^])\s*\d+\s*$`
Agent: `math_agent`
Why: `matched_R1_math`

**R2 — Profile lookup**
Pattern: “my favorite” OR write command
Agent: `profile_agent`
Why: `matched_R2_profile`

**R3 — Fact lookup**
World fact queries
Agent: `knowledge_agent`
Why: `matched_R3_knowledge`

**R4 — Fallback**
Agent: `generic_agent`
Why: `matched_R4_fallback`

## 5. Replay Equality Requirements

Replay must match EXACTLY on these fields:
- `router_decision`
- `selected_agents`
- `agent_outputs`
- `sem_reads`
- `sem_writes`
- `final_output`
- `council_votes`
- `claims`
- `evidence_items`
- `brainstate_before`
- `brainstate_after`

Any mismatch = `REPLAY_MISMATCH` error.
