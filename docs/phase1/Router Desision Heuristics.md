Router Decision Heuristics — Stage-1 (Final, Deterministic)

Purpose (one line)
Deterministically map a job’s query + BrainState hints + candidate modules → one ordered list of agent candidates with depth & token budgets, using only snapshot-driven, replayable inputs (no live nondeterministic metrics).

Core principles (must always hold)

Snapshot-driven — router reads the SelfRepresentation snapshot and BrainState snapshot referenced by the job’s ReflectiveLog; decisions must be reproducible from those snapshots + job_seed.

Deterministic scoring — every selection is computed from deterministic math; tie-breakers are deterministic (lexicographic).

Policy-first — module policy.forbidden_actions can veto routing; veto wins over score.

Availability-based — primary input = availability_score (SelfRep) & BrainState candidate_bias. No live telemetry influences choice.

Governed fallbacks — if no candidate passes threshold, deterministically pick fallback or raise ROUTER_NO_MATCH per Stage-0 rules.

Audit & snapshot — router decision object is stored in ReflectiveLog and must include router_snapshot_id and trace_id.

Inputs (must be provided / snapshotted)

job_id, job_seed (seeded RNG source)

query_text (normalized)

brainstate_snapshot (includes attention_gain, explore_bias, resource_budget, goals)

selfrep_snapshot (includes modules map, edges, apt, status, policy)

candidate_list (optional): explicit candidates from QCP; otherwise router enumerates allowed agents per query type.

router_config (snapshot): thresholds, weights, deterministic tie-break ordering.

Outputs (deterministic)

ordered_candidates: list of {node_id, availability_score, final_score, reason_tag} sorted desc by final_score

selected_agent: first candidate satisfying {allowed, score >= MIN_SCORE} or null

depth: integer (0..snapshot.max_depth_allowed) chosen deterministically

token_budget: integer allocated (≤ brainstate.resource_budget.token_budget)

route_trace: deterministic trace used for audit (all intermediate scores and tie-breaks)

All fields written to ReflectiveLog.

Default router constants (stored in snapshot)

MIN_AVAILABILITY = 0.15

MIN_SCORE = 0.2

WEIGHT_AVAIL = 0.7 (importance of availability_score)

WEIGHT_GOAL = 0.2 (priority weight from active goal)

WEIGHT_BIAS = 0.1 (BrainState candidate_bias influence)

DEP_UNHEALTHY_PENALTY = 0.5 (applied multiplicatively if dependency_unhealthy)

MAX_DEPTH_SAFEGUARD = snapshot.max_depth_allowed (router cannot exceed)

These values are part of router_config and must be saved in snapshot.

Exact deterministic scoring formula

For each candidate node n considered:

Read:

avail = selfrep.modules[n].apt * status_weight(status)
where status_weight = {healthy:1.0, degraded:0.6, offline/quarantined:0.0}

If edge.required == true && dependency_unhealthy == true then avail *= DEP_UNHEALTHY_PENALTY

goal_priority = highest-priority active goal that the candidate can serve ∈ [0,1] (derived deterministically from BrainState goals and node capabilities). If none, 0.0.

bias_factor = 1.0 if BrainState.candidate_bias.prefer_high_APT true and avail >= availability_median(snapshot) else 1.0 (used below as multiplicative tie-breaker; see tie rules).

Raw score:

raw_score = WEIGHT_AVAIL * avail + WEIGHT_GOAL * goal_priority + WEIGHT_BIAS * (BrainState.explore_bias * (1 - avail))


(Note: BrainState.explore_bias * (1 - avail) increases score for exploration when avail is low.)

Final score:

final_score = clamp(raw_score, 0.0, 1.0)


Candidate is allowed if:

policy.forbidden_actions does not block the query intent (mechanical check), AND

avail >= MIN_AVAILABILITY, AND

node.status != offline/quarantined

Only allowed candidates proceed. If none allowed, use fallback rules.

Depth & token budgeting (deterministic rules)

Compute base_depth = snapshot.max_depth_allowed (from BrainState.resource_budget)

Compute depth_multiplier = floor( attention_gain * base_depth ) where attention_gain ∈ [0,1] from BrainState.

depth = min(base_depth, max(0, depth_multiplier))

If attention_gain < 0.2 then depth = 0 (quick mode)

token_budget allocation:

token_budget = floor( brainstate.resource_budget.token_budget * (0.5 + 0.5 * attention_gain) )

Guarantee token_budget >= MIN_TOKEN_FLOOR (snapshot constant, e.g., 128)
All derived deterministically and saved in route output.

Tie-breaking (deterministic)

If two candidates have identical final_score (within machine epsilon), tie-break by:

higher apt (compare numeric)

lower node_id lexicographic (deterministic final fallback)

No randomness allowed.

Fallback & repair rules (deterministic)

If no allowed candidate with final_score >= MIN_SCORE:

If generic_agent available and allowed → select generic_agent with depth=0 and record reason_tag = "fallback_generic".

Else, return ROUTER_NO_MATCH error with deterministic user message per Stage-0.

If chosen candidate later fails (agent timeout/exception) during execution, router must re-run with:

removed candidate from candidate_list (append-only change in route_trace),

deterministic decrement of max_attempts (from snapshot),

new selection computed deterministically (replayable).

Each rerun iteration must be appended to the same ReflectiveLog entry (iteration_trace).

Security & policy checks (always before scoring)

Enforce policy.forbidden_actions per module: if a module is forbidden to perform action_type (e.g., SEM_write), it must be excluded.

If user role lacks permission for a module (RBAC check), exclude module.

If PII/private intent detected → block routing and return PRIVACY_BLOCKED.

All checks logged.

Router APIs (exact)

POST /router/decide payload (snapshotted IDs + query):

{
  "job_id":"...", "job_seed":"...", "query_text":"...", "selfrep_snapshot_id":"...", "brainstate_snapshot_id":"...", "candidate_list":[...], "trace_id":"..."
}


Response (deterministic):

{
  "ordered_candidates":[{"node_id":"...","availability_score":0.8,"final_score":0.72,"reason":"match_goal"}...],
  "selected_agent":"agent:logic_v1",
  "depth":1,
  "token_budget":1024,
  "route_trace": { /* deterministic details */ },
  "router_snapshot_id":"...", "trace_id":"..."
}


All calls append a router_decision record to append-only log.

Integration points & call order (deterministic workflow)

Executor reads selfrep_snapshot_id & brainstate_snapshot_id from ReflectiveLog.

Executor calls POST /router/decide with seeded inputs.

Router returns selected_agent + depth + token_budget.

Executor calls agent; any failures cause deterministic re-route (append iteration).

Final router_decision object goes into the ReflectiveLog for the job.

Golden test scenarios (must be in Stage-1 CI)

R-T1 — Basic selection

SelfRep: two agents A(apt=0.9,healthy) and B(apt=0.7,healthy). BrainState: attention_gain=0.8, no goal. Expect A chosen.

R-T2 — Goal bias

B is the only agent that matches goal capability; A has higher apt but doesn’t handle goal. Router must pick B if WEIGHT_GOAL pushes score above A.

R-T3 — Dependency unhealthy penalty

A depends on required db which is unhealthy. avail_A reduced by DEP_UNHEALTHY_PENALTY. If that drops final_score below B, router selects B.

R-T4 — Policy veto

A would be chosen by score but policy.forbidden_actions forbids required action; router must exclude A.

R-T5 — Depth calculation

Given max_depth_allowed=3, attention_gain=0.4 → depth = floor(0.4*3)=1. Assert depth.

R-T6 — Tie-breaker deterministic

Two nodes same final_score and apt — choose lexicographically lower node_id.

R-T7 — Fallback selection

No candidate passes MIN_SCORE but generic_agent exists → router selects generic_agent with depth=0.

R-T8 — Reroute on failure

Selected agent times out; router reruns deterministically excluding that node and appends iteration. New chosen agent recorded.

All tests must pin router_config, snapshots, and job_seed.

Edge cases & safeguards

Missing snapshot: reject with ROUTER_NO_SNAPSHOT error (developer message included).

Empty candidate_list: router enumerates allowed agents by query intent deterministically (use QCP mapping snapshot).

Huge candidate set: limit to top-N by apt prefilter (N in snapshot, default 10) to bound compute — selection of top-N deterministic.

Replay mode: router uses snapshot + job_seed only. No live recalculation.

Audit volume: store full route_trace but cap string lengths (artifact_url pattern for large traces).

Implementation notes for Ayushmaan

Implement router/decide to accept snapshot IDs, read snapshot JSONs from DB, compute all scores purely from those JSONs + job_seed.

All constants (weights, thresholds) must be values inside router_snapshot and saved in job ReflectiveLog.

Use deterministic float math (consistent rounding) across languages — define NUMERIC_EPSILON = 1e-9 and a canonical float formatting for logs.

Tests must freeze job_seed and snapshot values.

Governance & safety

Router cannot choose a module with status == quarantined.

Any change to router weights/constants requires a Stage-1 config PR + new snapshot and must be included in reflog for traceability.

High-risk actions (SEM writes, module policy changes) must be flagged by router decision output (e.g., requires_action_request: true) so executor triggers ActionRequest flow instead of immediate execution.