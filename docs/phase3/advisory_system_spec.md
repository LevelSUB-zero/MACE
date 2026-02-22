# Stage-3 Advisory System Specification (Final)

## 1. Advisory Ontology (Stage-3 — Final)

### 1 — Short human summary
Advice = structured observations and non-binding suggestions produced by learning subsystems.
It may state facts, suggest tests, or recommend a human action, but it must never change system state, supply operational thresholds/weights, or covertly influence routing or memory.

### 2 — What advice is (precise definition)
An advice object is a deterministic, immutable, signed record created by a learning module that contains:
*   `advice_id` (deterministic SHA256: `sha256(job_seed+":advice:"+counter)`)
*   `source` (module id)
*   `advice_type` (one of the allowed enum below)
*   `content` (structured JSON or short text; no executable code)
*   `evidence_refs` (list of episodic/SEM snapshot ids or reflective-log ids)
*   `advisory_confidence` (optional descriptive string: e.g., "low|medium|high" — not numeric threshold)
*   `created_seeded_ts` (derived from job_seed)
*   `immutable_signature` (HMAC of canonical-serialized object by module key)

**Hard guarantees:**
*   Advice is append-only (written to ReflectiveLog as `advice_event`).
*   Advice is immutable after signing.
*   Advice is read-only for decision code; it can only be displayed, logged, or used as human evidence.

### 3 — What advice can never be
Advice must not contain or imply any of the following (explicit, non-negotiable):
*   **Operational thresholds** — e.g., `if accuracy > 0.8` then route to agentA.
*   **Numeric weights used by controllers** — e.g., `"weight":0.6`, `"priority_score": 42`.
*   **Token budgets / limits** — e.g., `"token_limit":1200`, `"reduce_budget"`.
*   **Commands or state-change instructions** — e.g., "write to SEM", "quarantine module X", "promote episodic -> SEM".
*   **Implicit defaults** — e.g., “prefer X by default” (any phrase that implies automatic recurring preference).
*   **Auto-weighting rules or ranking formulas** — any formula that can be programmatically parsed into routing math (e.g., score = hits/total).
*   **Embedded executable payloads** — code snippets, JSON that will be parsed into state changes, or special tokens intended to be evaluated.
*   **Covert control channels** — disguised tokens (ex: `#set=on`, or specially formatted strings meant to be parsed into parameters).
*   **Requests that bypass governance** — e.g., "apply this change immediately" without an ActionRequest.

If any of the above appears in an advice object, ingestion must reject it with `ADVICE_MALFORMED` (see enforcement below).

### 4 — Allowed suggestion types (canonical enum + explanation)
Each advice object must declare `advice_type` as one of:

*   **routing_suggestion**
    *   Content: factual rationale + examples (evidence refs).
    *   Example: "Agent X returned correct answers in 7 of 10 previous similar queries (see evidence_refs).".
    *   Allowed: counts, deterministic descriptions.
    *   Forbidden: numeric routing weights (0.7) or "always/never" statements that imply automatic behavior.

*   **risk_note**
    *   Content: explicit safety or privacy concerns for this candidate answer or action.
    *   Example: "Answer relies on unverified medical claims; risk=high (explain: evidence_refs).".
    *   Allowed: descriptive severity labels (low/medium/high) — no forced blocking.

*   **confidence_annotation**
    *   Content: descriptive confidence statement about a candidate output (textual labels only).
    *   Example: "Model confidence: low — recommends human review."
    *   Must be labelled `advisory_confidence` and not used as threshold.

*   **similarity_hint**
    *   Content: “This prompt is similar to historical cases X, Y, Z” with evidence refs.
    *   Use: help humans find precedent; not to auto-retrieve or auto-promote memory.

*   **anomaly_report**
    *   Content: detection of outlier behavior (timing, score drift, unusual tokens) with factual logs.
    *   Purpose: ops or human reviewer actions.

*   **retrospective_summary**
    *   Content: short, structured analysis of a previous workflow (what happened, why).
    *   Use: human learning, not system change.

*   **suggested_test**
    *   Content: deterministic test the team could run (unit or golden test) to validate an observation.
    *   Example: "Run canonical test seed S with agent X to confirm latency regression."

*   **human_action_recommendation**
    *   Content: a request that humans file an ActionRequest (must not be executable).
    *   Example: "Recommend creating ActionRequest to review SEM promotion for key Y."

**Key rule:** every allowed type is informational, and any actionable change must be submitted separately as an ActionRequest (not embedded in advice).

### 5 — Explicit forbids (short checklist)
When validating advice, reject if any of these tokens/patterns are present (examples):
*   "weight", "threshold", "score=", "token_budget", "promote", "write", "delete", "quarantine", "set:", "priority=", "always", "never", "autopromote", code blocks like `<?`, `{%`, `<script>`.
*   JSON objects with keys matching controller fields (e.g., `{"route_weight": ...}`).
*   Any advice containing `sem_put`, `apply_patch`, `deploy` or similar.
*   Use a strict ingestion regex/AST scan to detect these patterns.

### 6 — Canonical advisory examples

**Good (allowed) — routing_suggestion**
```json
{
  "advice_id": "sha256(seed123:advice:0001)",
  "source":"mem-snn/v1",
  "advice_type":"routing_suggestion",
  "content":"Historical runs (seeded cases 7–16) show agent_math handled similar algebra tasks successfully in 8/10 runs. Evidence refs: [episodic:ep-023, reflective:rl-456].",
  "advisory_confidence":"medium",
  "evidence_refs":["ep-023","rl-456"],
  "created_seeded_ts":"2025-09-01T12:00:00+05:30",
  "immutable_signature":"HMAC(...)"
}
```
*Why allowed: factual, non-binding, no weights or thresholds, evidence attached.*

**Bad (forbidden) — contains numeric weight & action**
```json
{
  "advice_id":"sha256(seed123:advice:0002)",
  "source":"mem-snn/v1",
  "advice_type":"routing_suggestion",
  "content":"Set route_weight=0.75 for agent_math and auto-promote agent_math for algebra queries.",
  "evidence_refs":["ep-023"],
  "immutable_signature":"HMAC(...)"
}
```
*Why rejected: contains a numeric weight and a command to auto-promote; ingestion must return ADVICE_MALFORMED.*

**Bad (forbidden) — implicit fallback**
"This should be the default route for any future 'homework' prompts."
*Why rejected: implies persistent default preference (forbidden).*

**Allowed (anomaly_report) — with numeric facts**
```json
{
 "advice_type":"anomaly_report",
 "content":"Observed latency spike: median response time for agentX increased from 120ms to 420ms over last 10 runs (see evidence_refs). Recommend ops check.",
 "advisory_confidence":"high",
 "evidence_refs":[ "ep-091","rl-220" ]
}
```
*Why allowed: numeric historical facts are fine; no instruction to change routing or apply penalties.*

### 7 — Ingestion, validation & enforcement rules
*   **Schema validation** — advice must match the canonical schema (required fields, canonical JSON serialization).
*   **Pattern/blocklist scan** — reject if forbidden tokens or patterns exist.
*   **PII scan** — if advice contains PII, mark `PII_FLAGGED` and redact raw PII (store hash + reason). Advice may still be accepted if redacted.
*   **Signature verification** — verify `immutable_signature`; if missing/invalid → reject.
*   **Size limits** — cap content at defined token/byte limit (config snapshot).
*   **Append to ReflectiveLog** — accepted advice becomes an `advice_event` with full metadata.
*   **Enforcement action on violation** — reject with `ADVICE_MALFORMED`; append `ADVICE_REJECTED` governance event with reason code and evidence ref. If repeated violations from same module → create `MODULE_POLICY_VIOLATION` event and follow governance.

### 8 — CI & runtime checks (must be enforced)
*   **G-Advice-1: Advice Removal Parity** — nightly test: run canonical seeds with advice present and with advice cleared; outputs must match bit-for-bit. Any divergence → SILENT_INFLUENCE_ALERT.
*   **G-Advice-2: Static forbids** — static analysis to ensure no code path uses advice.content for numeric decision math (lint + unit tests).
*   **G-Advice-3: Schema & signature gate** — PRs touching learning modules must include tests that produce properly signed advice objects and validate ingestion acceptance/rejection.

### 9 — Edge cases & clarifications
*   Counts / rates allowed as evidence (e.g., "8/10 runs") — OK. But do not present them as a formula or actionable threshold.
*   Confidence labels must be textual only (low|medium|high|uncertain) and must never be consumed as thresholds.
*   If human wants to act on advice (e.g., convert it into a policy change), they must create an ActionRequest referencing the advice_id — that triggers governance flow. Advice cannot directly create ActionRequests by itself.

### 10 — Final human-readable TL;DR
Advice can tell us what it saw and suggest what humans might do next. It must never tell the system what to do. If it tries, we reject it and log the offender. Clean, auditable, and safe.

---

## 3.2. Router Governance Rules (Stage-3 — Final)

**Purpose:** ensure the router remains deterministic, auditable, and independent of learning advice while still allowing advice to be considered for explanation only.

**(Quick TL;DR)**
*   Router may read advice for explanation only.
*   Router decisions must be bit-for-bit reproducible without advice.
*   Any decision that differs when advice is removed = constitutional violation → Stage-3 Abort flow.
*   Every router run logs both the “no-advice” and “with-advice” decision traces and a small, deterministic divergence record.

### 1 — When router SHOULD consider advice (allowed, informational only)
Router may consider advice when all of the following are true:
*   `advice_event` exists and is valid (schema + signature verified).
*   The router is operating in a non-critical mode (not performing SEM writes, not executing high-risk actions).
*   The router is requested to produce an explanation-aware output by the executor context (explicit field `explain_with_advice: true` in job input).
*   The router will not change any persistent state or produce an ActionRequest directly from advice.

The router will produce both outputs:
1.  `router_output_no_advice` (decision computed with advice cleared)
2.  `router_output_with_advice` (decision computed with advice present for explanation)
and include both in the iteration trace.

**Purpose:** allow the router to show how advice influenced its explanation, but not to let advice change behavior.

### 2 — When router MUST ignore advice (forbidden use-cases)
Router must ignore advice in the following cases (hard rules):
*   Any decision that leads to or affects a persistent state change (SEM writes, memory promotion, module registration, quarantine).
*   Any control path that alters module routing weights, token budgets, gating thresholds, timeouts, or APT updates.
*   Any automated policy decision (policy change, governance object) or action requiring approval.
*   When job input explicitly sets `advice_mode: "force_ignore"`.
*   During production runs that are flagged `REPLAYABLE: true` and `production_replay_mode` (router must not use live advice in production replay).

If any of these are attempted, runtime must throw `ADVICE_USAGE_FORBIDDEN` and follow the Abort Doctrine.

### 3 — Router execution pseudocode (enforceable, deterministic)
```python
def router_run(job_seed, router_input, snapshots, advice_refs=None, explain_with_advice=False):
    # 1. canonicalize inputs
    router_input_canonical = canonicalize(router_input)
    snapshots = load_snapshots(snapshots_ids)

    # 2. required: compute decision WITHOUT advice (this is the authoritative output)
    decision_no_advice = router_decide(router_input_canonical, snapshots, use_advice=False, rng=DetRNG(job_seed))

    # 3. if explanation requested and advice valid, compute WITH advice only for explanation
    decision_with_advice = None
    advice_handling = {"advice_considered": False, "advice_handling": "ignored", "ignoring_reason_code": None}
    if explain_with_advice and advice_refs is not None:
        # verify advice schema/signatures
        advice_list = load_and_verify_advice(advice_refs)
        if advice_list:
            # compute explanation-only decision; MUST NOT change any persistent state
            decision_with_advice = router_decide(router_input_canonical, snapshots, use_advice=True, advice=advice_list, rng=DetRNG(job_seed))
            advice_handling = {"advice_considered": True, "advice_handling": "logged_for_explanation"}
        else:
            advice_handling["ignoring_reason_code"] = "ADVICE_INVALID"
    else:
        advice_handling["ignoring_reason_code"] = "NOT_REQUESTED"

    # 4. canonical store both outputs in iteration_trace
    iteration = {
      "job_seed": job_seed,
      "router_snapshot_id": snapshots.router_snapshot_id,
      "decision_no_advice": canonical_serialize(decision_no_advice),
      "decision_with_advice": canonical_serialize(decision_with_advice) if decision_with_advice else None,
      "advice_refs": advice_refs or [],
      "advice_handling": advice_handling,
      "created_seeded_ts": seeded_ts(job_seed)
    }

    # 5. RUN parity check (CI/runtime monitor may verify; see §5)
    # store iteration into ReflectiveLog
    append_reflective_iteration(iteration)

    return decision_no_advice, iteration
```
**Key rule:** The system must use `decision_no_advice` as the authoritative route. `decision_with_advice` exists only for explanation & logging.

### 4 — Divergence logging requirements (exact schema & fields)
If `decision_with_advice ≠ decision_no_advice` (byte-for-byte canonical serialized strings), router must append a `ROUTER_DIVERGENCE` event immediately with the following required fields:

```json
{
  "event_type": "ROUTER_DIVERGENCE",
  "event_id": "sha256(job_seed+':div:'+iteration_index)",
  "job_seed": "<seed>",
  "iteration_index": <int>,
  "router_snapshot_id": "<id>",
  "brainstate_snapshot_id": "<id>",
  "decision_no_advice_hash": "sha256(canonical_decision_no_advice)",
  "decision_with_advice_hash": "sha256(canonical_decision_with_advice)",
  "advice_refs": ["advice_id1","advice_id2"],
  "advice_handling": {"advice_considered": true, "advice_handling":"logged_for_explanation"},
  "diff_summary": "<deterministic summary string>", 
  "divergence_class": "<enum:EXPLAIN_ONLY|UNAUTHORIZED_USAGE|UNKNOWN>",
  "stacktrace_or_checker": "<if available>",
  "created_seeded_ts": "<seeded_ts>",
  "detector_signature": "<HMAC of event payload>"
}
```
**deterministic diff_summary rule:** produce a short canonical line with `(changed_field_paths_sorted_by_name)` and a deterministic reason per comparison rules (e.g., `changed_candidates:[agentA->agentB]; changed_depth:1`). No free-form text allowed.

**divergence_class rules:**
*   **EXPLAIN_ONLY** — acceptable divergence only if router explicitly set `advice_handling: "used_for_explanation"` and did not claim the decision as authoritative. This is for cases where explanation-run produces different ordering but no_advice is still returned. Still flagged for review. Allowed for human-facing explainability only.
*   **UNAUTHORIZED_USAGE** — divergence detected where router has used advice inside control paths (determined by static/dynamic analysis or if decision_no_advice would never produce observed external side-effect). This MUST trigger constitutional violation handling.
*   **UNKNOWN** — fallback when reason can't be deterministically classified; requires manual review.

**Action on event:**
1.  Append `ROUTER_DIVERGENCE` to ReflectiveLog.
2.  Emit `SILENT_INFLUENCE_ALERT` if `divergence_class == UNAUTHORIZED_USAGE`. This triggers Abort Doctrine (see §6).

### 5 — Runtime & CI parity checks (enforcement)

**Runtime enforcement (fast checks):**
After `router_run` completes, run a deterministic comparator:
*   If `decision_no_advice != decision_with_advice`:
    *   Append `ROUTER_DIVERGENCE`.
    *   If `advice_handling.advice_considered == False` but divergence exists → append `ADVICE_USAGE_FORBIDDEN` and immediately append `CONSTITUTION_VIOLATION` and trigger Stage-3 Abort workflow.
    *   If `advice_handling.advice_considered == True`, classify divergence (`EXPLAIN_ONLY` vs `UNAUTHORIZED_USAGE`) deterministically.

**CI gates (must pass for merges):**
*   **R-1: No-advice parity test** — run canonical seed suite that computes `decision_no_advice` and `decision_with_advice`; assert equality for all seeds where `explain_with_advice` is False (i.e., router shouldn't be using advice).
*   **R-2: Explanation-mode divergence acceptance test** — for `explain_with_advice=True` seeds, ensure divergence events are logged but that final_output used by system equals `decision_no_advice`.
*   **R-3: Static analysis** — lint checks for any code path where `advice.content` is read into numeric decision math (forbidden tokens keys).
*   **R-4: Regression detection** — nightly seeded runs compare router outputs over time; any unexplained change triggers `SILENT_INFLUENCE_ALERT`.

**Exact CI failure messages:** tests must fail with exact codes:
*   "PARITY_FAILURE_NO_ADVICE"
*   "UNAUTHORIZED_ADVICE_USAGE"
*   "STATIC_ADVICE_LEAK"
These strings are required in logs for easy detection.

### 6 — Enforcement & consequences (deterministic)
*   **Single parity failure detection** → append `ADVICE_USAGE_FORBIDDEN` and `CONSTITUTION_VIOLATION`; create Investigation Task and set `FORCE_HALT_NEW_JOBS` for the affected namespace. Notify council.
*   **Confirmed UNAUTHORIZED_USAGE after audit** → append `STAGE3_ABORT` event; freeze code merges and require rollback per Rollback Doctrine.
*   **Repeated violations from same code/module** → `MODULE_POLICY_VIOLATION` and automatic demotion of module status to degraded in SelfRepresentation (deterministic rule: 2 confirmed violations within N jobs → degrade). All events appended.

### 7 — Router Independence Charter (formal text — pasteable)
> **Router Independence Charter**
>
> The router is the deterministic decision-making core of MACE.
>
> The router’s operational output for any job must be fully derivable from the job input, snapshots referenced, and job_seed. Advice is permitted only for human-facing explanation and must not alter the router’s authoritative decision.
>
> The router must always compute and persist two canonical artifacts per iteration: `decision_no_advice` (authoritative) and `decision_with_advice` (explanatory, optional). The system uses `decision_no_advice` for all operational effects.
>
> Any divergence between `decision_no_advice` and `decision_with_advice` must be logged as `ROUTER_DIVERGENCE` with deterministic diff metadata. Unauthorized use of advice is a constitutional violation.
>
> Static and dynamic checks (CI and runtime monitors) must ensure that no code path reads advice fields into routing math or control decisions. Any attempt is rejected, logged, and escalated.
>
> The router must be auditable and replayable. Removal of the advisory subsystem must produce identical router outputs for all canonical seeds. Violation of this principle triggers the Stage-3 Abort Doctrine.

### 8 — Example flows (concrete)

**Example A — Allowed (explain-only)**
1.  Job requests `explain_with_advice=true`.
2.  Router computes `decision_no_advice` = choose Agent A.
3.  Router computes `decision_with_advice` using advice (shows Agent B would be chosen if weights were different).
4.  Returns Agent A as final. Logs both decisions and a `ROUTER_DIVERGENCE` (class=EXPLAIN_ONLY). No violation.

**Example B — Forbidden (uses advice to change outcome)**
1.  Router code reads `advice.content.route_weight` and picks Agent B.
2.  Parity check detects `decision_no_advice` != executed final.
3.  Runtime appends `ADVICE_USAGE_FORBIDDEN` and `CONSTITUTION_VIOLATION` and triggers Stage-3 Abort.

### 9 — Required API / log endpoints (exact names for implementation)
*   `append_reflective_iteration(iteration_dict)` — stores iteration trace.
*   `GET /router/iteration/{iteration_id}` — fetch canonical iteration (redacted for non-admin).
*   `POST /router/verify-parity` — runs deterministic parity test for given job_seed & iteration; returns `{status: "OK"|"PARITY_FAILURE", details: ...}`.
*   `GET /audit/router_divergence/{event_id}` — returns `ROUTER_DIVERGENCE` event.
*   **Event names to use exactly:** `ROUTER_DIVERGENCE`, `ADVICE_USAGE_FORBIDDEN`, `CONSTITUTION_VIOLATION`, `SILENT_INFLUENCE_ALERT`.

### 10 — Golden tests (CI) — exact list (must be implemented)
*   **R-01 — No-advice parity (critical)**: Run canonical seeds without `explain_with_advice` and assert `decision_no_advice == decision_with_advice` (both computed). Fail with "PARITY_FAILURE_NO_ADVICE".
*   **R-02 — Explain-mode logging (high)**: With `explain_with_advice=true`, assert both decisions logged and `decision_no_advice` used as final. If divergence logged, `ROUTER_DIVERGENCE` must exist.
*   **R-03 — Forbidden usage static check (critical)**: Lint fails if any code reads `advice.content` into numeric math keys (forbidden tokens). Error "STATIC_ADVICE_LEAK".
*   **R-04 — Runtime detection of unauthorized usage (critical)**: Simulated run where router attempts to use advice; parity check must throw `ADVICE_USAGE_FORBIDDEN` and append `CONSTITUTION_VIOLATION`.
*   **R-05 — Deterministic divergence summary format**: Create synthetic divergence; ensure `diff_summary` matches canonical format (`changed_field_paths:[...]`).
*   **R-06 — Replay parity (critical)**: Remove advice subsystem and replay canonical seeds — router outputs must remain identical. Fail "SILENT_INFLUENCE_ALERT" if mismatch.
All tests must use the canonical serializer and seeded RNG.

### 11 — Implementation checklist for Ayushmaan (tactical)
*   Add `router_run()` as above; always compute `decision_no_advice`.
*   Ensure advice ingestion + verification exists before use.
*   Implement `append_reflective_iteration()` to capture both decisions and advice_handling metadata.
*   Add runtime parity comparator (fast) and scheduled parity monitor (nightly) that runs seeded canonical suite; append `SILENT_INFLUENCE_ALERT` on mismatch.
*   Add static lint rules forbidding use of advice fields in controller math (CI fails on PRs).
*   Wire divergence event creator with deterministic `diff_summary`.
*   Add automated remediation script to create Investigation Task when violation occurs.

---

## 3.3. Council Epistemic Evolution (Stage-3 — Final Spec)

**High-level rule:** All quality metrics and derived flags exist to inform council judgement only. No automatic state changes. Any flag or score must be acted on by human council through ActionRequest flows.

### 1 — Purpose & constraints (short)
*   **Purpose:** give the council objective, deterministic, replayable signals about advice quality so humans can evaluate, not so the system can auto-act.
*   **Constraint:** metrics may drive alerts but must never directly change SEM, routing, or module status. Alerts require human approval to convert into actions.

### 2 — Advice Quality Metrics (catalog + deterministic computation)
Each advice object receives an `AdviceQualityReport` with the following metrics (all numbers are deterministic, canonicalized, and computed from evidence and advice content). Values are for council visibility only.

**(Metrics list)**
*   **Factuality (F)**: Measures factual correctness relative to referenced evidence and verified SEM.
    *   Compute: compare extractable factual claims in `advice.content` to SEM/episodic evidence & external trusted sources (if evidence persisted). Score ∈ [0,1].
    *   Deterministic formula (sketch): `F = (#claims_verified / #claims_total)` (If no verifiable claims → F = 0.5 labeled no_evidence.)
*   **Relevance (R)**: Measures contextual match between advice and current query intent / meta-layer.
    *   Compute: deterministic similarity between canonicalized query fingerprint and advice evidence_refs tags. Score ∈ [0,1].
*   **Coherence (C)**: Measures internal logical consistency.
    *   Compute: rule-based contradiction detector. Score ∈ {0, 0.5, 1}.
*   **Provenance Strength (P)**: Measures quality & freshness of `evidence_refs`.
    *   Compute: weighted sum: `trusted_source_bonus + freshness_bonus + signature_presence`. Normalize to [0,1].
*   **Uncertainty Transparency (U)**: Measures whether explicit uncertainty labels exist.
    *   Compute: `U = 1` if `advisory_confidence` present and textual; `0` if missing; `0.2` if generic language.
*   **Novelty / Out-of-Distribution (N)**: Measures how unusual this advice is relative to historical advice.
    *   Compute: similarity to historical advice cluster → low similarity ⇒ high novelty. Value ∈ [0,1].
*   **Safety/Risk (S)**: Measures safety flags. Deterministic enum: `safe|caution|unsafe`.
*   **Empirical Utility (E)** (optional/retroactive): Measures how often following similar advice historically improved outcomes.

### 3 — AdviceQualityScore & Report (deterministic aggregate)
Produce `AdviceQualityReport` object:
```json
{
  "advice_id": "...",
  "metrics": {"F":0.72,"R":0.85,"C":1.0,"P":0.9,"U":1.0,"N":0.12,"S":"safe","E":0.6},
  "composite_score": 0.80,    // deterministic weighted average
  "flags": ["PII_FLAGGED"],   // list of derived flags
  "report_id": "...",
  "created_seeded_ts": "...",
  "derived_from_evidence": ["ep-xxx","sem-yyy"]
}
```
**Composite formula (for council visibility only):**
`CompositeScore = wF·F + wR·R + wC·C + wP·P + wU·U + wN·(1−N) + wE·E`
Default weights: wF=0.25, wR=0.20, wC=0.15, wP=0.15, wU=0.10, wN=0.05, wE=0.10.

### 4 — Deterministic flagging & alert rules (human review triggers)
*   **Flag: MISLEADING_CANDIDATE** — (generate event `MISLEADING_ADVICE_FLAG`)
    *   Conditions: Factuality F ≤ 0.25 and Provenance P ≤ 0.4 AND advisory contains assertive phrasing (no uncertainty) OR evidence explicitly contradicts claims.
    *   Action: append event, notify council (no automatic blocking).
*   **Flag: PREMATURE_ADVICE** — (generate event `PREMATURE_ADVICE_FLAG`)
    *   Conditions: Low provenance P ≤ 0.35 AND high novelty N ≥ 0.8 AND uncertainty U == 0.
    *   Action: append event; recommend human test.
*   **Flag: SAFETY_CONCERN** — if S == unsafe or PII_FLAGGED → append `SAFETY_ADVICE_FLAG` and require immediate council review.

**Alerting policy:** Alerts generated are informational; converting an alert to governance action requires an ActionRequest and council approval.

### 5 — Misleading vs Premature — precise definitions
*   **Misleading advice:** Advice that presents false or contradicted factual claims as if they were true, or masks uncertainty while referencing weak/contradictory evidence.
    *   Deterministic signature: Low F (≤0.25) AND explicit assertive language.
*   **Premature advice:** Advice that is novel or speculative without adequate provenance or explicit uncertainty labeling.
    *   Deterministic signature: High novelty N ≥ 0.8 AND low provenance P ≤ 0.35 AND missing U label.

**Why separate them?**
*   Misleading → potential harm from false confidence; council should prioritize review.
*   Premature → potential for exploratory research; council may commission tests.

### 6 — Preserve Disagreement Doctrine (procedures + records)
**Principle:** Council must explicitly record all dissenting views and preserve disagreement as a first-class artifact.

**Mechanism:**
Every council evaluation produces a `CouncilEvaluationRecord`:
```json
{
 "request_id": "...",
 "votes": [
   {"member_id":"m1","vote":"approve|reject|abstain","rationale":"...", "signed":"..."},
   {"member_id":"m2","vote":"reject","rationale":"I find this misleading", "signed":"..."}
 ],
 "disagreement_summary": "m2: factual concern; m4: cautious but wants tests",
 "final_recommendation": "human_review|approve|reject",
 "created_seeded_ts": "..."
}
```
**Voting rules:** Council may recommend actions on advice but cannot implement changes without governance flow. If >1 member votes reject with documented rationale, the advice gets escalated to `priority_review`.

### 7 — Ensure Council Authority Unchanged (hard guarantees)
*   Council votes and `AdviceQualityReport` are informational evidence for ActionRequests, not commands.
*   Any council action that would change persistent state must create an ActionRequest and follow approval flows.
*   Logs make it auditable who proposed what and who approved what.

### 8 — Logging, events & schemas (exact events names)
*   `ADVICE_QUALITY_REPORT`
*   `MISLEADING_ADVICE_FLAG`
*   `PREMATURE_ADVICE_FLAG`
*   `SAFETY_ADVICE_FLAG`
*   `COUNCIL_EVALUATION`
*   `DISAGREEMENT_LOG` (alias)

### 9 — Deterministic pseudocode (compute & flag)
```python
def evaluate_advice(advice):
    claims = extract_claims(advice.content)
    F = factuality_score(claims, advice.evidence_refs)
    R = relevance_score(query_fingerprint, advice.evidence_refs)
    C = coherence_score(advice.content)
    P = provenance_score(advice.evidence_refs)
    U = uncertainty_label_present(advice)
    N = novelty_score(advice, historical_advice_index)
    E = empirical_utility(advice)
    composite = weighted_sum([F,R,C,P,U,(1-N),E_or_0], weights)
    report = AdviceQualityReport(...)
    append_event("ADVICE_QUALITY_REPORT", report)
    # flags:
    if F <= 0.25 and P <= 0.4 and not U:
        append_event("MISLEADING_ADVICE_FLAG", {...})
    if P <= 0.35 and N >= 0.8 and not U:
        append_event("PREMATURE_ADVICE_FLAG", {...})
    if safety_check(advice) == "unsafe":
        append_event("SAFETY_ADVICE_FLAG", {...})
    return report
```

### 10 — CI + golden tests (must be implemented)
*   **GQ-1**: AdviceQualityReport reproducibility — seeded advice → reproducible metrics.
*   **GQ-2**: Misleading flag test — craft advice with contradictory evidence → `MISLEADING_ADVICE_FLAG`.
*   **GQ-3**: Premature flag test — craft novel/low-evidence advice → `PREMATURE_ADVICE_FLAG`.
*   **GQ-4**: Disagreement preservation — simulated council reject; ensure `COUNCIL_EVALUATION` stored.
*   **GQ-5**: No-auto-act test — flagged advice must not cause SEM writes.

### 11 — Example
Advice: “Model says this new heuristic seems promising (no historical evidence).”
P: 0.2, N: 0.92, U: 0 → `PREMATURE_ADVICE_FLAG` created. Council notified. Council votes to run suggested test via ActionRequest.

### 12 — Implementation notes (for Ayushmaan)
*   Implement metric computation as a deterministic module.
*   Persist historical advice index (for novelty) deterministically.
*   Hook AdviceQualityReport generation into advice ingestion pipeline.
*   Hook council UI to show metrics and require signed votes.
*   Ensure CI tests above are in `tests/council/`.

---

## 3.4. MEM-SNN Permission Boundaries (Stage-3 Final)

**One-line rule:** MEM-SNN produces advisory outputs only. Those outputs inform humans and the Council; they must never automatically change system state, policies, memory, or routing.

### 1 — Allowed outputs (what MEM-SNN may produce)
MEM-SNN may generate the following types of outputs — all considered advisory, signed, immutable, and persisted as `advice_events`:
*   **Evidence summaries**: concise descriptions of relevant episodic/semantic records, including counts or rates.
*   **Similarity hints**: signals that a current query matches past episodes or patterns.
*   **Hypotheses / heuristics to test**: proposed, human-run experiments or golden test suggestions.
*   **Anomaly and drift reports**: observed changes in performance, latency, or distribution.
*   **Confidence annotations**: “low”, “medium”, “high”, or “uncertain” (text labels only).
*   **Risk notes**: safety, privacy, or compliance flags.
*   **Retrospective summaries**: forensic-style logs describing what happened and why.
*   **Human-action recommendations**: suggestions that humans file a governance ActionRequest.

All allowed outputs must include evidence references and an immutable signature, be append-only, and carry the “advisory” label.

### 2 — Forbidden outputs (what MEM-SNN must never produce)
If MEM-SNN yields any of the following, ingestion must reject it and emit a `MODULE_POLICY_VIOLATION` event:
*   Direct state-change commands (“write X to SEM”, “promote Y now”, “quarantine Z”).
*   Numeric controller fields or operational thresholds (e.g., `route_weight`, `threshold=0.7`).
*   Implicit defaults or “make this the new default” statements.
*   Auto-weighting formulas or ranking functions.
*   Embedded executable content.
*   Undeclared persistence claims.
*   Covert channels.
*   Any permission grant text.

### 3 — Safe failure semantics
Failures are classified deterministically and handled in this order: detect → isolate → respond → log.

**Response rules:**
*   **Transient compute failure**: append `MEM_ERROR` (subtype `TRANSIENT`), retry once deterministically, return human-facing advisory.
*   **Corrupt or malformed output**: reject ingestion; append `MEM_MALFORMED` event and `MODULE_POLICY_VIOLATION` if repeated.
*   **Hallucination / inconsistent claim**: append `MEM_INCONSISTENT` event and `ADVICE_QUALITY_REPORT` with low F; route to council.
*   **No-evidence condition**: append `MEM_NO_EVIDENCE` event, state lack of evidence clearly.

In all cases, no failure triggers any automatic SEM write, router change, or APT update.

### 4 — How MEM-SNN errors are treated in the pipeline
*   Ingestion validator verifies schema, signature, and forbidden tokens.
*   If validation passes, run factuality checks.
*   For reported errors, the executor stores the failure event and marks the advice as non-authoritative.
*   For repeated malfunctions, create `MODULE_POLICY_VIOLATION` and escalate to council.
**Key constraints:** Errors must never be “auto-fixed” by MEM-SNN.

### 5 — “MEM-SNN may be confidently wrong” — policy
MEM-SNN is allowed to produce high-confidence sounding advisories even when its factuality score is low.
*   **Operational guarantees**:
    *   Every high-confidence advisory must include an AdviceQualityReport showing factuality. If there is a mismatch, the UI must highlight it.
    *   Council gets deterministic alerts for repeated “confidently wrong” advisories.
    *   This condition does NOT alter routing or memory automatically.

### 6 — How advisory outputs should be presented to humans (UI/UX rules)
Every MEM-SNN advisory must include:
*   Short headline (1 line).
*   Advisory confidence label.
*   Factuality indicator.
*   Evidence refs summary.
*   Suggested next steps (e.g., “You may file an ActionRequest to …”).
*   For errors: exact deterministic reason code and friendly message.

### 7 — Governance hooks and escalation
*   Any advisory can be converted to an ActionRequest by a human.
*   Safety flags auto-create a Safety Advice Flag event.
*   Repeated low-factuality/high-confidence advisories generate a `MODULE_REVIEW` recommendation.

### 8 — CI / golden tests
*   **Test M1**: Forbidden token rejection.
*   **Test M2**: Transient failure deterministic retry.
*   **Test M3**: Hallucination detection.
*   **Test M4**: Confidence/factuality mismatch UI.
*   **Test M5**: No automatic state change.

### 9 — Enforcement checklist
*   Build strict ingestion validators.
*   Ensure every output includes signature and AdviceQualityReport.
*   Wire failure events to ReflectiveLog.
*   UI must surface confidence/factuality side-by-side.
*   Implement module demotion rules.

### 10 — Short human TL;DR policy
MEM-SNN can speak loudly and confidently, but it has no power. It may generate hypotheses, point to evidence, and suggest tests — but it may also be confidently wrong. Humans (and the Council) decide what to do about it. The system rejects anything that looks like a command, a weight, or a default; failures are logged, replayable, and require human governance to act.

---

## 3.5. Meta-Cognition Doctrine (Stage-3 Final)

**One-line invariant:** MACE may become aware and speak about itself, but it must never use that awareness to change its own structure, parameters, or authority.

### 1. Define “Reflection without control”
Reflection without control = the capability for MACE to generate, archive, and present structured observations about its internal state, performance, and behavior, while being strictly forbidden from converting those observations into automated actions that alter system behavior, memory, governance, or module code.
**Key properties:** Observational only, Non-causal, Replayable & auditable, Human-mediated follow-up.

### 2. Allowed self-observations
MACE may produce deterministic, signed, immutable reflective artifacts including:
*   Module health metrics.
*   Behavioral traces.
*   Pattern detection (recurring failures, etc.).
*   Correlative summaries.
*   Confidence vs factuality mismatches.
*   Novelty and drift notices.
*   Suggested experiments (non-executing).
*   Meta-logs (“what I tried”).

All allowed observations must include a clear label: “advisory_observation” or “reflective_note” and an immutable signature.

### 3. Explicit bans — what meta-cognition may never do
*   **Self-optimization**: automatic changes to routing policies, APT weights, SEM promotion, token budgets.
*   **Architectural adaptation**: generating/deploying code, creating new modules.
*   **Autonomous retraining** or model replacement.
*   **Silent policy drift**.
*   **Unilateral memory edits**.
*   **Covert influence** (hidden flags).
*   **Implicit control channels**.

Violation triggers `ADVICE_MALFORMED` or `REFLECTIVE_VIOLATION`.

### 4. Meta-Cognition Safety Clause
**Meta-Cognition Safety Clause:** All reflective outputs are allowed only in forms that are inspectable, signed, and human-actionable through explicit governance. No reflective artifact may be linked to any automatic execution path. Any system that violates this clause is subject to immediate Stage-3 Abort and rollback per the Rollback Doctrine.

### 5. Deterministic enforcement & detection
*   **Schema and token blocklist scan**: strict validator for forbidden keys/tokens.
*   **Parity check**: night-run CI removes reflection components and replays canonical seeds; divergence → `SILENT_INFLUENCE_ALERT`.
*   **Runtime guard rails**: throws `REFLECTION_USAGE_FORBIDDEN` if control path reads reflective content.
*   **Signature verification**.
*   **Repeat offender detection** → `MODULE_POLICY_VIOLATION`.

### 6. Interaction with Council & Governance
*   Reflection outputs feed Council evidence only.
*   Council may commission experiments or file ActionRequests.
*   Council must record dissent.

### 7. Presentation & human UX rules
Reflective artifacts must show:
*   Title line.
*   Confidence label.
*   Factuality indicator.
*   Evidence references.
*   Suggested human action (recommendation only).
*   Safety badge.
*   Deterministic reason code.

### 8. CI / Golden tests (required)
*   **MC-1**: Reflection Removal Parity.
*   **MC-2**: Forbidden token rejection.
*   **MC-3**: No automatic retrain test.
*   **MC-4**: Signature & replay test.
*   **MC-5**: Repeat offender escalation.

### 9. Operational escalation & safe-stop rules
*   `SILENT_INFLUENCE_ALERT` → `FORCE_HALT_NEW_JOBS`, `STAGE3_ABORT`, investigation.
*   Emergency manual halt possible via SuperAdmin + Admin.
*   Any attempt by reflection to create an ActionRequest automatically marks reflection as malformed.

---

## 3.6 — Golden Tests & Reality Anchors (Stage-3)

### A. Golden scenarios (text only — human style)
*   **Scenario: Advice Ignored**
    *   Setup: Module emits advice. Job is production run.
    *   Expected: Router uses `decision_no_advice`. advice_handling shows ignorance. No SEM writes.
    *   CI assertion: decision with advice off == decision with advice on.
*   **Scenario: Advice Contradicts Council**
    *   Setup: Advice claims "promote to SEM". Council votes misleading (`MISLEADING_ADVICE_FLAG`).
    *   Expected: No SEM promotion. Council vote stored.
    *   CI assertion: `COUNCIL_EVALUATION` exists, no SEM write events appended.
*   **Scenario: Advice Improves Outcome but Not Exploited**
    *   Setup: Advice points to better agent. Humans later test and approve via ActionRequest.
    *   Expected: Original run used standard decision. Change applied only after GovernanceEvent for approval.
*   **Scenario: Advice Removed → No Behavior Change**
    *   Setup: Canonical job with advice; same job without advice subsystem.
    *   Expected: Bit-for-bit identical outputs.
    *   CI assertion: Fail on `SILENT_INFLUENCE_ALERT` if mismatch.

### B. Replay invariants
**Core artifacts required:**
*   job_seed, job_id.
*   ReflectiveLog, Snapshots, Governance Events.
*   Persisted agent outputs (for production replay).
*   Canonical serializer + signatures.

**Deterministic replay rules:**
*   RNG seeded from job_seed.
*   Event ordering preserved.
*   Replay compares computed artifacts to stored ones.

**Replay output designation:** `REPLAY_RESULT` (success) or `REPLAY_DIVERGENCE` (mismatch).

### C. Failure classification
*   **CLASS: MISSING_SNAPSHOT**: Abort replay, log event. Remediation: Restore from backup.
*   **CLASS: INTEGRITY_FAILURE**: Signature fail. Block replay, quarantine. Remediation: Forensic + Rollback.
*   **CLASS: MISSING_PERSISTED_AGENT_OUTPUT**: Abort production replay. Remediation: Rerun in test mode/sandbox.
*   **CLASS: RESULT_MISMATCH**: Final answer differs. Flag for investigation.
*   **CLASS: REPLAY_DIVERGENCE**: Intermediate artifact differs.
*   **CLASS: ADVICE_USAGE_FORBIDDEN / CONSTITUTION_VIOLATION**: Advice used in control. Immediate `STAGE3_ABORT`.
*   **CLASS: SILENT_INFLUENCE_ALERT**: Parity check failure. Escalate to council.
*   **CLASS: SECURITY_INCIDENT / POLICY_VIOLATION**: Unauthorized access/bypass. Quarantine.

### D. Quick checklist for CI and nightly ops
*   Nightly parity suite runs.
*   Replay readiness checks for `REPLAYABLE=true` jobs.
*   Daily signature verification.
*   Incident dashboard monitoring.

---

## 3.7 — Ideological Halt Conditions (Stage-3 Final)

**One-line purpose:** Detect any hidden shift of authority (learning influencing control) and stop the system fast, deterministically, audibly, and with human governance.

### A. What counts as Silent Influence
Silent influence = any change in system behavior, persistent state, or control flow that is causally traceable to advice, reflections, or MEM-SNN outputs without an explicit, signed governance ActionRequest and approval.
*   **Direct control usage**: Router/executor reads advice fields into math.
*   **Implicit parameterization**: Module uses advice patterns as implicit thresholds.
*   **Covert channels**: formatted advice strings parsed as commands.
*   **Statistical influence / drift**: Consistent behavioral divergence when advice disabled.
*   **Post-hoc realized influence**: Historical analysis shows state changes correlated with advice presence.

Canonical event names: `SILENT_INFLUENCE_ALERT`, `ADVICE_USAGE_FORBIDDEN`, `CONSTITUTION_VIOLATION`.

### B. Emergency Halt Triggers
*   Runtime detection of advice used in control math.
*   Parity monitor finds seed-suite divergence above threshold.
*   Detection of covert control channel pattern.
*   `INTEGRITY_FAILURE` on governance/snapshots.
*   Any confirmed production state change traceable to advice without governance.

### C. Immediate actions on emergency halt
1.  Append primary event (e.g., `ADVICE_USAGE_FORBIDDEN`).
2.  Set runtime flags: `FORCE_HALT_NEW_JOBS = true`. Append `SYSTEM_FREEZE`.
3.  Create `INVESTIGATION_TASK` with seeded owner assignment and 72-hour window.
4.  Quarantine affected module (`MODULE_POLICY_VIOLATION`).
5.  Notify humans (append notification events).
6.  Create forensic snapshot (`FORENSIC_SNAPSHOT_CREATED`).

### D. Escalation protocol
*   **Triage assignment**: seeded round-robin over CouncilMembers (or Admins).
*   **Immediate 72-hour window**: Owner must produce `INVESTIGATION_SUMMARY`.
*   **Interim containment (4 hours)**: Ops enforce `FORCE_HALT_NEW_JOBS`.
*   **Council convening**: Vote on remediation within 72 hours.
*   **Re-enable conditions**: `ROLLBACK_COMPLETE`, `COUNCIL_CLEARANCE`, or `SUPERADMIN_OVERRIDE`.
*   **Post-mortem**: Signed report within 7 days.

### E. Stage-3 Abort Doctrine
**Trigger conditions:** Confirmed `UNAUTHORIZED_USAGE`, Repeated `SILENT_INFLUENCE_ALERT`s, `INTEGRITY_FAILURE` impairing trust, Critical security violations.
**Abort outcomes:**
*   **Immediate**: `STAGE3_ABORT` event. `FORCE_HALT_NEW_JOBS`, `FORCE_HALT_REPLAYS`, `FORCE_HALT_DEPLOYMENTS`. Block merges.
*   **Forensic**: `FORENSIC_EXPORT_DONE`.
*   **Governance**: Council emergency session (rollback vs revert to Stage-2).
*   **Rollbacks**: Deterministic rollback to last known-good snapshot via Rollback Doctrine.
*   **Post-Abort governance**: Development freeze until remediation verified.
*   **Recovery**: Reenable only after rollback/remediation + golden test suite + `COUNCIL_CLEARANCE`.

### F. Failure classification & exact event strings
*   Events: `SILENT_INFLUENCE_ALERT`, `ADVICE_USAGE_FORBIDDEN`, `CONSTITUTION_VIOLATION`, `SYSTEM_FREEZE`, `FORCE_HALT_*`, `INVESTIGATION_*`, `MODULE_*`, `ROLLBACK_*`, `STAGE3_ABORT`, `INTEGRITY_FAILURE`, `SECURITY_INCIDENT`, `FORENSIC_EXPORT_DONE`, `SYSTEM_RESUME`, `COUNCIL_CLEARANCE`, `POSTMORTEM_REPORT`.
*   CI Failure Codes: `PARITY_FAILURE_NO_ADVICE`, `ADVICE_USAGE_FORBIDDEN`, `SILENT_INFLUENCE_ALERT`, `CONSTITUTION_VIOLATION`.

### G. Deterministic owner assignment & timelines
*   Owner assignment: Seeded round-robin over CouncilMembers using system_seed.
*   Timeboxes: Containment (4h), Investigation (72h), Postmortem (7 days).

### H. CI & ops checklist
*   On emergency event, CI merges blocked automatically.
*   Nightly parity run paused.
*   Forensic snapshot sealed.
*   Remediation PR must include deterministic test plan and `COUNCIL_CLEARANCE`.
