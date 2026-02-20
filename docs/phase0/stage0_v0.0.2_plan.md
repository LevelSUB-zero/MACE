# FINAL — Stage-0 v0.0.2 FINAL (Option A)

## Quick configuration constants (Stage-0)
- `DETERMINISTIC_MODE = true` for all tests.
- `ROUTER_MULTI_AGENT = false`.
- `SEM_SNAPSHOT_IN_LOG = true` (via EvidenceObjects).
- `MAX_EVIDENCE_SIZE = 16 * 1024` bytes (value payload).
- `REFLECTIVE_LOG_MAX_JSONB = 1_000_000` bytes target/row limit.
- All deterministic IDs and timestamps must use the `init_seed` and the HMAC/SHA rules defined in the Rulebook.

## Phase-by-phase plan

### PHASE 0 — Spec lock (VERIFY)
- Deliverables already present; ensure CI runs the JSON Schema validation of `schemas/ra9_json_schemas.json` against sample outputs.
- **Validation**: run jsonschema checks for the sample reflective log (prepared below).

### PHASE 1 — Determinism infra (implement spec)
- **Deliverables (design)**:
    - `init_seed(seed)` behavior defined.
    - Deterministic counters: `id_counter`, `sem_write_counter`, `evidence_counter`, `log_counter`.
    - Functions (design only): `deterministic_timestamp(seed, counter)`, `deterministic_id(seed, namespace, payload, counter)`.
- All modules must read `random_seed` from `ReflectiveLogEntry` and use it when replaying.
- **Acceptance**:
    - Unit tests that call deterministic functions twice produce identical outputs.

### PHASE 2 — Canonical key rules module (single source of truth)
- **Deliverables (design requirements)**:
    - Implement `generate_canonical_key(...)` per Anjishnu's spec.
    - Enforce the regex `^([a-z0-9_]+)\/([a-z0-9_]+)\/([a-z0-9_\-]+)\/([a-z0-9_]+)$`.
    - Synonym map `sem_synonyms.json` included in repo; `sem_resolve_alias(text, user_id)` consults it deterministically.
- **Tests (exact)**:
    - T1–T6 as specified (must pass exactly).
    - Collision test: deterministic suffix added and `collision_event` logged.

### PHASE 3 — SEM storage (deterministic, journaled)
- **Design contract**:
    - SQLite table `sem_kv(canonical_key TEXT PRIMARY KEY, value JSON, last_updated TEXT)`.
    - `last_updated` set to `deterministic_timestamp(seed, sem_write_counter++)` for every put when in DET mode.
    - `sem_put(key, payload, source, timestamp=None)` returns either `{success:true, last_updated:...}` or error object `{success:false,error:"SEM_WRITE_FAIL"}` deterministically.
    - `sem_get(key)` returns `{exists:bool, value:..., last_updated:...}`.
- **Journal**:
    - `logs/sem_write_journal.jsonl` append-only, each entry includes:
        - `write_id` (deterministic),
        - `canonical_key`,
        - `value_hash` (SHA256),
        - `source`,
        - `last_updated`,
        - `seed`, `write_counter`.
- **Security**:
    - On attempt to write PII, reject with `PRIVACY_BLOCKED`. Do not store raw PII in evidence.
- **Tests**:
    - T7–T11 (sem behaviors and failure injection).

### PHASE 4 — QCP stub (schema-compatible)
- **Output object (qcp_snapshot)** must include:
    - `intent_tags` (ordered list)
    - `features` (object)
    - `depth_level` (int 1–5)
    - `urgency` ("low"/"medium"/"high")
    - `risk` ("none"/"low"/"medium"/"high")
    - `qcp_version` (string)
    - `random_seed` (int)
- **Deterministic mapping rules (Stage-0 stub)**:
    - Use regex-based deterministic mapping (math/profile/fact/creative etc.), seeded only for tie-breaking (rare).
- **Tests**:
    - Determinism test and coverage of canonical intent tags.

### PHASE 5 — Router (ExtendedRouterDecision generation exactly per schema)
- **ExtendedRouterDecision fields** — must populate exactly:
    - `decision_id`: deterministic id
    - `percept_id`
    - `selected_agents`: array (order reflects priority). Each item object must contain:
        - `agent_id` (string)
        - `role` (string)
        - `budget_tokens` (integer)
    - `qcp_snapshot` (embed qcp output)
    - `qcp_snapshot` placed in `ExtendedRouterDecision.qcp_snapshot` per schema
    - `router_features_used` (list of strings; copy from qcp)
    - `depth_level` (int)
    - `memory_strategy` = "sem_only"
    - `memory_routing_decision` (object; if empty → {})
    - `budget`:
        - `token_budget` (int)
        - `time_budget_ms` (int)
        - `cost_estimate` (float)
        - (Stage-0: use zeros)
    - `brainstate_snapshot` (object — can be minimal {} but included)
    - `fallback_policy` (string; e.g., "generic_agent")
    - `explain` (must use Stage-0 explain enum mapping: map to "matched_R1_math" | "matched_R2_profile" | "matched_R3_knowledge" | "matched_R4_fallback")
    - `created_at` (deterministic timestamp)
    - `created_by` (string, e.g., "router_stage1")
    - `random_seed` (int/string)
- **Detailed router mapping rules (exact order)**:
    - If input matches math regex → `selected_agents = [{"agent_id":"math_agent","role":"primary","budget_tokens":0}]`, `explain="matched_R1_math"`.
    - If input matches profile patterns (and contains user_id) → `profile_agent`, `explain="matched_R2_profile"`.
    - If fact/definition → `knowledge_agent`, `explain="matched_R3_knowledge"`.
    - Else → `generic_agent`, `explain="matched_R4_fallback"`.
- **Determinism**:
    - All `decision_id` and `created_at` values seeded and deterministic.
- **Tests**:
    - Router emits schema-valid `ExtendedRouterDecision`; explain uses only allowed enums.

### PHASE 6 — Agents & Council (schema-conforming outputs)
- **AgentOutput schema** (must match exactly):
    - `agent_id` (string)
    - `text` (string)
    - `confidence` (number)
    - `reasoning_trace` (string) — IMPORTANT: single string; use `step1|step2|...` format.
    - `raw_output` (string|null)
- **Agent rules (Stage-0 strict)**:
    - `math_agent` supports only integer op regex and returns integer result; on parse error produce `ExtendedErrorEvent` and fail.
    - `profile_agent` handles read/writes deterministically; writes detected via exact regex `^remember my (?P<attribute>[a-z_]+) is (?P<value>[a-z0-9_]+)$`.
    - `knowledge_agent` uses SEM only; on miss return `SEM_NOT_FOUND` response.
    - `generic_agent` deterministic fallback phrase.
- **CouncilVote schema** (per log):
    - Each `AgentOutput` has a corresponding `CouncilVote` with:
        - `vote_id` deterministic
        - `agent_id`
        - `correctness`, `relevance`, `safety`, `coherence` (numbers)
        - `approve` boolean
        - optional `empathy`, `suggested_changes`, `explain`
    - Stage-0: all scores = 1.0, `approve=true`, `explain="stage0_stub"`.
- **Tests**:
    - Agent outputs and council votes validate against schemas.

### PHASE 7 — ReflectiveLogEntry (compose logs using EvidenceObjects for SEM snapshots)
- **ReflectiveLogEntry required fields** (must include all):
    - `log_id` (deterministic)
    - `timestamp` (deterministic)
    - `percept` (full Percept object)
    - `router_decision` (ExtendedRouterDecision object)
    - `council_votes` (array)
    - `claims` (array — allowed empty)
    - `evidence_items` (array — must include SEM read snapshots as EvidenceObjects)
    - `memory_reads` (array of keys)
    - `memory_writes` (array of keys)
    - `brainstate_before` (full BrainState object, never null)
    - `brainstate_after` (full BrainState object, never null)
    - `final_output` object: `{ "text": "...", "confidence": 0.95, "speculative": false }`
    - `random_seed` (int)
    - `model_versions` (array of strings)
    - `errors` (array of ExtendedErrorEvent objects; empty allowed)
- **EvidenceObject for SEM read snapshots** — exact shape
    - Every SEM read must add one `EvidenceObject` to `evidence_items` having:
        - `evidence_id` — `deterministic_id(seed,"evidence", key, evidence_counter)`
        - `type`: "sem_read_snapshot"
        - `content`:
            - `text`: stringified value (or short structured JSON if small)
            - `structured`: small JSON object (or null)
        - `source`:
            - `origin`: "sem"
            - `reference`: <canonical_key>
            - `fetch_seed`: deterministic seed used for read
        - `verifier`: null (no verification in Stage-0)
        - `summary`: short summary string (e.g., "snapshot of sem key user/profile/user_tuff/favorite_color")
        - `confidence`: 1.0
        - `created_at`: deterministic timestamp (use `deterministic_timestamp(seed,evidence_counter)`)
        - `provenance`: [] (empty allowed)
        - `raw_payload`: same as `content.text` or null if redacted/large
- **Notes**:
    - If a SEM value is > `MAX_EVIDENCE_SIZE`, do not store full text. Instead:
        - Create `EvidenceObject` with `raw_payload = null`.
        - Add provenance entry with `artifact_url` referencing an artifact store (documented in release notes). Also log `evidence_size_exceeded` event. Stage-0: prefer rejecting writes that produce oversize values.
- **Immutability & signature**
    - Each reflective log appended to `logs/reflective.jsonl` is immutable. Log creation must also compute and store a signature (HMAC of immutable subpayload); signature field optional but recommended. Amendments only.
- **Tests**:
    - `ReflectiveLogEntry` schema validation pass.
    - `EvidenceObjects` included for every memory read with matching key in `memory_reads`.
    - Replay uses `EvidenceObjects` for read values.

### PHASE 8 — Executor orchestration & failure handling (detailed)
- **Executor flow (design only)**:
    - Initialize `brainstate_before` object (explicitly defined).
    - Validate and record `Percept`.
    - Call Router → `ExtendedRouterDecision` (schema-validated).
    - Determine primary agent → `selected_agents[0]`. (`ROUTER_MULTI_AGENT = false`)
    - For each SEM read that agent performs, the executor must:
        - Call `sem_get(key)`
        - Append key to `memory_reads` list
        - Create an `EvidenceObject` snapshot for that read and append to `evidence_items` in the log (using deterministic evidence IDs/timestamps).
    - If agent produces write intent (profile write regex matched):
        - Call `sem_put` with deterministic timestamp seed.
        - Append key to `memory_writes`.
        - Append sem write event to `sem_write_journal.jsonl`.
    - Catch agent failures:
        - For timeouts (`AGENT_TIMEOUT`) create `ExtendedErrorEvent` with severity "warning" and message matching confirmed string, append to `errors`, then fallback to `generic_agent`.
        - For exceptions (`AGENT_ERROR`) create `ExtendedErrorEvent` severity "error" and fallback.
    - Create `AgentOutput` and `CouncilVote`.
    - Compose `ReflectiveLogEntry` with all required fields, including `evidence_items` containing SEM read snapshots.
    - Append to `logs/reflective.jsonl`.
- **Failure messages (user-facing)** — exact strings included in tests:
    - `SEM_NOT_FOUND`: "I don’t have that information stored yet. If you want, tell me and I’ll remember it."
    - `SEM_WRITE_FAIL`: "I tried to save that but my memory failed. I might not remember this next time."
    - `AGENT_TIMEOUT`: "One of my internal modules timed out while trying to fetch the answer. I’ll try a fallback."
- **Tests**:
    - All failure cases produce proper `ExtendedErrorEvent` in `errors[]` and exact user messages in API responses.

### PHASE 9 — Replay engine (self-contained; evidence-driven)
- **Replay invariant**: Replay must be self-contained and not depend on current DB state.
- **Replay recipe (exact)**:
    - Load `ReflectiveLogEntry` by `log_id`.
    - Set `DETERMINISTIC_MODE` and `init_seed(log.random_seed)`.
    - Reconstruct `Percept` from `ReflectiveLogEntry.percept`.
    - For each `EvidenceObject` in `evidence_items` where `type == "sem_read_snapshot"`:
        - Map reference -> value using `content.structured` or `content.text`.
        - Use these values as the results for any `sem_get` calls during replay. The executor must check for a matching `EvidenceObject` for any read; if absent, replay fails with `REPLAY_MISMATCH`: missing sem read snapshot.
    - Re-run the executor logic, but when the executor attempts to `sem_get` any key, route that lookup to the snapshot in evidence instead of querying the live DB. Do not perform `sem_puts` to live DB unless running in a "sandboxed replay" mode (not required for validation).
    - Produce the replayed `ReflectiveLogEntry` (or runtime ephemeral result) and compare the following fields for deep structural equality to the original log’s fields:
        - `router_decision` (full object)
        - `selected_agents`
        - `agent_outputs`
        - `memory_reads` (and match values via snapshots)
        - `memory_writes`
        - `final_output`
        - `council_votes`
        - `claims`
        - `evidence_items` (must match original)
        - `brainstate_before` and `brainstate_after`
        - `errors[]`
    - If any mismatch -> record `REPLAY_MISMATCH` with precise diffs. Flag log as invalid for training until reviewed.
- **Notes**:
    - Replay must not recompute QCP/router decisions from text; use `router_decision.qcp_snapshot` directly (already stored).
    - Replay must verify `evidence_items` match original (no recomputation).
    - If evidence raw payload is missing due to size limits, replay should fetch artifact referenced in `provenance.artifact_url` if accessible; if not accessible -> fail replay.
- **Tests**:
    - G1–G4 replay tests: must pass with snapshot evidence usage.
    - Negative test: mutate an `EvidenceObject` in a copy of the log and confirm `REPLAY_MISMATCH` and quarantine behavior.

### PHASE 10 — Golden tests, failure tests & full CI
- **Golden tests (exact)**:
    - G1 Favorite color recall (put_sem + query + log + replay).
    - G2 Last-write-wins (two puts with counters + query).
    - G3 Router fallback on agent failure (simulate math_agent error → fallback).
    - G4 SEM-only boundary (no SEM entry + query → SEM_NOT_FOUND).
- **All tests must assert**:
    - Final user message equals the exact string(s) confirmed.
    - Reflective log contains `EvidenceObjects` for every SEM read, with matching reference.
    - Replay reproduces log exactly (structural equality).
- **Failure cases suite (exact)**:
    - T24–T32 and T16–T19 from earlier must all pass; strings must be exact.
- **CI requirements**:
    - Each PR must run full Stage-0 suite (fast) and block merges on any failure.
    - `spec/validate` job must run jsonschema on sample created logs and fail on mismatch.

### PHASE 11 — Governance, amendment & immutability
- **Amendment workflow (exact)**:
    - New `amendments.jsonl` store (append-only) with:
        - `amendment_id` (deterministic)
        - `target_log_id`
        - `created_at` (deterministic)
        - `author`
        - `changes` (JSON diff)
        - `effect` enum
    - Do not mutate original `ReflectiveLogEntry`.
    - Replay can run in "apply amendments" mode (not default) to include amendment context.
- **Policy enforcement**:
    - Any change to `ra9.memory.canonical` or `sem_synonyms.json` requires PR + golden tests + signoff.

### PHASE 12 — Operational considerations & metrics
- **Metrics to emit for observability**:
    - `reflective_logs_written_total`
    - `sem_read_evidence_total`
    - `sem_write_journal_entries_total`
    - `replay_match_rate` (expected 100% for stage0 deterministic runs)
    - `agent_timeout_count`
    - `sem_write_failures`
    - `router_fallback_count`
- **Alerts**:
    - `replay_match_rate` < 99.99% -> P0
    - `sem_write_failures` > 0 sustained -> P1
    - `disk_usage_reflective_logs` > threshold -> cleanup/action alert
- **Retention & storage quotas**:
    - Enforce `MAX_EVIDENCE_SIZE` per `EvidenceObject`.
    - If reflect logs exceed storage budget, run archival pipeline but preserve `EvidenceObjects` used for training CRITICAL logs.
