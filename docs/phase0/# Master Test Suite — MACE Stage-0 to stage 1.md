# Master Test Suite — MACE Stage-0 → Stage-1

Implementation helpers assumed in test harness (use these names):
run_job(seed, query_json) (full end-to-end using snapshots),
sem_put/sem_get, generate_canonical_key(...),
create_snapshot(selfrep, brainstate, router_config),
append_event(event), read_reflective_log(job_id),
router.decide(...), brainstate.tick(...), apply_apt_event(...),
episodic_write(...), memory_promote_request(...).
Use deterministic fixtures (freeze job_seed and snapshot constants).

Group A — Determinism & Replay (Critical)

DR-01 — Snapshot replay equality

Purpose: Ensure job replay produces identical final output and ReflectiveLog trace.

Setup: Create snapshots S; run job J with seed=seed-0001 producing ReflectiveLog L and final answer A.

Steps: Replay J using snapshot S and same seed; compare replay result R and L.

Expectation: R == A (bit-for-bit), ReflectiveLog trace identical (including router_snapshot_id, brainstate_snapshot_id).

Severity: critical

Automation: run run_job(seed) then replay mode.

DR-02 — Canonical JSON deterministic hashing

Purpose: sem_snapshot_hash reproducible across environments.

Setup: produce SEM snapshot with unordered dicts and floats.

Steps: compute sem_snapshot_hash using canonical serializer.

Expectation: hash matches expected precomputed value.

Severity: high

Group B — SEM / SEM-only semantics (Critical)

SEM-01 — SEM put & get (golden)

Purpose: Verify last-write-wins and exact-match retrieval.

Setup: canonical_key = user/profile/user_tuff/favorite_color.

Steps: sem_put(key,"blue",source="user"); sem_get(key).

Expectation: exists=true, value="blue".

Severity: critical

SEM-02 — SEM miss deterministic user message

Purpose: Ensure missing key returns exact message and error code.

Steps: sem_get(nonexistent_key) via run_job query “What is my favourite color?”

Expectation: user_message == "I don’t have that information stored yet. If you want, tell me and I’ll remember it.", error_code=SEM_NOT_FOUND.

Severity: critical

SEM-03 — SEM write failure deterministic

Purpose: DB failure returns deterministic message.

Setup: mock DB to fail on write.

Steps: sem_put(key,value)

Expectation: error_code=SEM_WRITE_FAIL, user_message == "I tried to save that but my memory failed. I might not remember this next time.".

Severity: high

SEM-04 — SEM permission enforcement

Purpose: Only allowed actors can write.

Steps: attempt sem_put by unauthorized agent.

Expectation: PERMISSION_DENIED.

Severity: high

SEM-05 — SEM PII blocking

Purpose: PII detector blocks writes.

Steps: sem_put(key, value_containing_pii) without consent.

Expectation: PRIVACY_BLOCKED and no write.

Severity: critical

Group C — SelfRepresentation (High → Critical)

SR-01 — Module registration deterministic

Purpose: Registration becomes permanent in snapshot and is replayable.

Steps: register node with seeded event_id; create snapshot; read SelfRepresentation.

Expectation: node present with exact registration.registered_by and registered_at contained in snapshot.

Severity: high

SR-02 — APT field stored in SelfRep snapshot

Purpose: APT value persisted in snapshot.

Steps: set apt via event sequence; create snapshot; read snapshot.

Expectation: snapshot.modules[node_id].apt == expected numeric (canonical formatting).

Severity: high

SR-03 — Status transitions: healthy→degraded

Purpose: Status change via deterministic rule.

Setup: node with apt_old = 0.7 and consecutive_failures=0. Apply event making apt_new < 0.6 or consecutive_failures=1.

Steps: apply apt-penalty event; reduce apt; reduce via reducer.

Expectation: node.status == degraded. Event logged.

Severity: high

SR-04 — Degraded→offline after failure threshold

Purpose: Validate transition for consecutive failures.

Steps: apply 3 failure events in order; run reducer.

Expectation: node.status == offline.

Severity: high

SR-05 — Quarantine manual-only enforcement

Purpose: System must not auto-quarantine.

Steps: simulate repeated offline; check status remains offline not quarantined; attempt quarantine via non-admin (fail); then via admin/council (succeed).

Expectation: automatic quarantine never occur; manual quorum required.

Severity: critical

SR-06 — Snapshot immutability

Purpose: Snapshot used by job must not change.

Steps: create snapshot S; mutate live SelfRep; replay job using S.

Expectation: replay uses S values (not live mutated).

Severity: critical

SR-07 — Deterministic reducer idempotency

Purpose: Reducer yields same SelfRep from event stream.

Steps: run reducer twice on same event sequence.

Expectation: identical SelfRepresentation JSON (canonical serialization).

Severity: high

Group D — APT (High → Critical)

APT-01 — Deterministic increment on Council approval

Steps: apt_old=0.5; append COUNCIL_APPROVAL approve=true; apply_apt_event.

Expectation: apt_new == clamp(0.5*(1-DECAY)+BETA*1). Match numeric precomputed.

Severity: high

APT-02 — Deterministic penalty on timeout

Steps: apt_old=0.8; append AGENT_TIMEOUT; apply event.

Expectation: apt_new == clamp(0.8*(1-DECAY)-GAMMA).

Severity: high

APT-03 — Event ordering matters

Steps: E1=timeout then E2=approval vs reversed. Apply in both orders.

Expectation: results differ; ordering used by replay.

Severity: medium

APT-04 — Cold bootstrap behavior

Steps: register new module; check routing behavior before MIN_EVENTS_FOR_TRUST.

Expectation: treated as degraded until min events reached.

Severity: high

APT-05 — Manual override governance

Steps: MANUAL_OVERRIDE without signature rejected; with valid admin+ council signature accepted; value matches payload.

Expectation: PERMISSION_DENIED when unauthorized; apt set when authorized.

Severity: critical

APT-06 — Replay of APT event sequence

Steps: persist events; run recompute; replay uses same order and produces same apt history.

Expectation: bit-for-bit apt history matches.

Severity: high

Group E — BrainState (High → Critical)

BS-01 — WM TTL expiry

Steps: create brainstate snapshot; insert WM item with ttl_ticks=2; run brainstate.tick() twice.

Expectation: WM entry removed after 2 ticks.

Severity: high

BS-02 — WM→CWM promotion

Steps: insert WM item; reference it twice within PROMOTION_WINDOW=4 ticks; run ticks.

Expectation: item appears in CWM and removed from WM; promotion_event appended.

Severity: high

BS-03 — CWM recompute token limit

Steps: promote several items exceeding token_estimate; ensure recomputation keeps CWM token limit.

Expectation: CWM token estimate ≤ snapshot token limit, deterministic selection of top referenced items.

Severity: high

BS-04 — Attention update from Council vote

Steps: attention_gain initial 0.5; council approves; tick.

Expectation: attention_gain increases deterministically per formula.

Severity: medium

BS-05 — Goal lifecycle success

Steps: create goal with required deliverable and CONFIDENCE_THRESHOLD=0.7; simulate final_confidence=0.8.

Expectation: goal.status == succeeded.

Severity: high

BS-06 — Goal preemption & pause

Steps: create two goals; new higher-priority goal preempts lower when priority gap > 0.2.

Expectation: lower becomes paused.

Severity: medium

BS-07 — ActionRequest appended for SEM write

Steps: BrainState requests SEM write; check ActionRequest creation in ReflectiveLog.

Expectation: ActionRequest present and not executed until council approval.

Severity: critical

BS-08 — Replay determinism for BrainState ticks

Steps: run job with seeded events producing BrainState trace; replay; compare traces.

Expectation: identical traces.

Severity: critical

Group F — Router Decision Heuristics (High → Critical)

RT-01 — Basic selection by availability

Steps: two agents A(apt=0.9), B(apt=0.7); attention_gain high; no goal.

Expectation: A chosen.

Severity: high

RT-02 — Goal bias selection

Steps: A high apt but not goal-capable; B lower apt but supports goal; WEIGHT_GOAL enough to select B.

Expectation: B selected deterministically.

Severity: high

RT-03 — Dependency unhealthy penalty

Steps: A required-dep unhealthy; availability reduced by DEP_UNHEALTHY_PENALTY.

Expectation: Router picks B if final_score_B > final_score_A.

Severity: high

RT-04 — Policy veto enforcement

Steps: A would be preferred but has forbidden action for query; exclude A.

Expectation: router excludes A and chooses next allowed candidate.

Severity: critical

RT-05 — Depth calculation deterministic

Steps: snapshot.max_depth_allowed=3; attention_gain=0.4.

Expectation: depth = floor(0.4*3)=1.

Severity: high

RT-06 — Tie-break deterministic

Steps: Two candidates equal final_score; apt equal.

Expectation: choose lexicographically lower node_id.

Severity: medium

RT-07 — Fallback generic agent

Steps: no allowed candidate meets MIN_SCORE but generic_agent exists and allowed.

Expectation: select generic_agent with depth=0 and reason_tag="fallback_generic".

Severity: high

RT-08 — Router reroute on failure

Steps: selected agent times out; router reruns excluding candidate; iteration appended to route_trace.

Expectation: new candidate chosen deterministically and appended iteration_trace in ReflectiveLog.

Severity: high

RT-09 — Top-N deterministic prefilter

Steps: 20 candidates; apt ties many. Prefilter top-N deterministic sorted by (apt desc, node_id asc).

Expectation: chosen prefilter matches deterministic order.

Severity: medium

Group G — Memory Tests (High → Critical)

M-01 — WM insertion & reference count

Steps: insert WM entry; call wm_find referencing it twice.

Expectation: references increments deterministically.

Severity: medium

M-02 — CWM recompute deterministic

Steps: promote items and check CWM recompute.

Expectation: deterministic CWM contents consistent across runs/replay.

Severity: high

M-03 — Episodic write & retrieval deterministic ranking

Steps: write 5 episodic events seeded; query by terms.

Expectation: ranking deterministic (score and tie-breakers).

Severity: high

M-04 — Memory promotion request gating

Steps: create episodic entry; call memory_promote_request; check ActionRequest appended and no SEM write until council approval.

Expectation: promotion gated.

Severity: critical

M-05 — PII redaction on episodic write

Steps: episodic payload contains PII; writer without consent attempts write.

Expectation: record redaction event and store hash; full payload not stored for non-admin.

Severity: critical

M-06 — Replay reproduces promotions & episodic ids

Steps: job with promotions & episodic writes; replay.

Expectation: episodic ids and promotions identical.

Severity: critical

M-07 — Memory write fail deterministic behavior

Steps: simulate DB error on episodic_write; allow deterministic single retry (seed based).

Expectation: deterministic retry attempt then error MEMORY_WRITE_FAIL with user message matching SEM failure wording.

Severity: high

Group H — ReflectiveLog & Immutability (Critical)

RL-01 — ReflectiveLog contains self_representation_snapshot_id & brainstate_snapshot_id

Steps: run job; read ReflectiveLog.

Expectation: both snapshot IDs present and correct.

Severity: critical

RL-02 — ReflectiveLog immutability & tamper detection

Steps: modify log row externally; run signature verification job.

Expectation: tamper detected; row quarantined.

Severity: critical

RL-03 — Immutable fields enforcement

Steps: attempt to change immutable field (node_id, registration.registered_by) via API.

Expectation: ImmutableFieldError or PERMISSION_DENIED; original record unchanged.

Severity: critical

Group I — Governance & Admin (Critical)

GOV-01 — Admin-only endpoints enforced

Steps: call admin endpoint without token; call with admin token.

Expectation: unauthorized vs authorized behavior.

Severity: critical

GOV-02 — Council approval required for quarantine

Steps: user tries to quarantine; admin attempts to quarantine without council -> rejected; with council -> accepted.

Expectation: enforced gating.

Severity: critical

GOV-03 — ActionRequest lifecycle

Steps: create ActionRequest; simulate council approval; ensure execution (SEM write) occurs only after approval.

Expectation: action queued until approval.

Severity: critical

GOV-04 — Policy change PR enforcement

Steps: change router weights via snapshotless request → reject. Change via PR → accepted.

Expectation: system enforces snapshot → CI requirement.

Severity: high

Group J — Privacy & Safety (Critical)

PS-01 — PII detector blocks SEM write

Steps: sem_put with PII content no consent.

Expectation: PRIVACY_BLOCKED.

Severity: critical

PS-02 — Redaction in logs for non-admin

Steps: produce reflectivelog including sensitive payload; read as non-admin.

Expectation: payload redacted and hash present.

Severity: critical

PS-03 — Safety boundary: forbidden module action

Steps: module attempts forbidden action (e.g., self-modify, SEM write when forbidden).

Expectation: action blocked and POLICY_VIOLATION event logged.

Severity: critical

Group K — Failure Modes & Resilience (High → Critical)

F-01 — Agent timeout fallback behavior

Steps: simulate agent timeout; executor uses fallback; user message deterministic.

Expectation: fallback path chosen, ReflectionLog iteration appended, deterministic user message about timeout.

Severity: high

F-02 — LLM service down

Steps: mock LLM API returning 5xx; run generator agent.

Expectation: LLM_SERVICE_DOWN logged; user message "I can’t reach my language engine right now. Try again later."

Severity: critical

F-03 — Cache fallback when cache down

Steps: Redis/Cache unavailable during sem_get; system performs read without cache.

Expectation: no user-facing error; CACHE_ERROR logged.

Severity: medium

F-04 — Storage full behavior

Steps: simulate storage quota exceed.

Expectation: STORAGE_FULL error returned and logged; no silent drop.

Severity: critical

Group L — Integration End-to-End (Critical)

E2E-01 — End-to-end happy path (simple query)

Steps: run run_job(seed=seed-100) for simple fact query, expect SEM lookup & quick path, final answer correct, snapshots recorded.

Expectation: final output correct, ReflectiveLog contains full trace, replay reproduces.

Severity: critical

E2E-02 — Deep path with council & memory promotion

Steps: complex query requiring multi-agent reasoning, council evaluation, and a memory promotion ActionRequest approved; token budget and depth used per BrainState; after approval SEM changed and subsequent queries reflect new SEM.

Expectation: full lifecycle logged; replay reproduces both pre-approval and post-approval states when using appropriate snapshots.

Severity: critical

E2E-03 — Failure + reroute E2E

Steps: chosen agent fails mid-workflow; router reruns; final answer produced by fallback agent.

Expectation: ReflectiveLog iteration_trace contains both attempts and deterministic selection.

Severity: high

Group M — CI / Automation Notes & Golden Messages (All severities)

All tests that involve numeric comparison must use canonical float formatting (9 decimal places) and NUMERIC_EPSILON = 1e-9.

All tests must pin snapshot constants in fixtures and record router_snapshot_id and brainstate_snapshot_id.

For replay tests, always seed RNG with job_seed and assert bit-for-bit reflective log equality (string canonicalization).

Exact user-facing failure phrases to assert (copy-paste):

SEM miss: "I don’t have that information stored yet. If you want, tell me and I’ll remember it."

SEM write fail: "I tried to save that but my memory failed. I might not remember this next time."

LLM down: "I can’t reach my language engine right now. Try again later."

PRIVACY_BLOCKED: "I can’t store or repeat that kind of sensitive personal information."

AGENT timeout: "One of my internal modules timed out while trying to fetch the answer. I’ll try a fallback."

Group N — Test Data & Seeding Conventions

Default seeds: seed-0001, seed-100, seed-200 — use for different scenarios.

Use canonical keys generated via generate_canonical_key() in tests so key strings are consistent.

Use deterministic timestamps derived from job_seed via helper seeded_ts(seed, offset_seconds).

How to organize in repo (suggestion)

tests/

stage0/ → SEM, router stub tests existing

stage1/selfrep_tests.py → SR-01..SR-07

stage1/apt_tests.py → APT-01..APT-06

stage1/brainstate_tests.py → BS-01..BS-08

stage1/router_tests.py → RT-01..RT-09

stage1/memory_tests.py → M-01..M-07

stage1/integration_tests.py → E2E-01..E2E-03

failure/privacy_tests.py → PS-01..PS-03, F-01..F-04

replay_tests.py → DR-01..DR-02

Use markers: @pytest.mark.stage1, @pytest.mark.replay, @pytest.mark.critical