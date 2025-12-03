MACE — Safety Boundaries (Stage-1 Final)

One-line purpose: Prevent harm, unauthorized change, data leak, runaway self-modification, or unsafe outputs by enforcing deterministic safety gates, governance checks, monitoring, and conservative defaults across the entire system.

1 — Overarching safety rules (non-negotiable)

Conservative default — in any uncertainty, MACE must choose the safest option (block, degrade, or require human review).

Deterministic enforcement — any safety decision that affects the workflow must be reproducible from job_seed + snapshots + ordered events. No live guesswork.

Append-only audit — every safety event (block, redaction, quarantine, override) is an append-only SafetyEvent recorded in ReflectiveLog with seeded event_id and signature.

Human-in-the-loop for high risk — any operation that could materially change the system state, harm a person, or persist sensitive PII requires an ActionRequest and the approval flow defined in Governance.

Fail-closed — if a required artifact for a safety decision is missing/corrupt, fail closed (halt / require admin) rather than proceed.

No autonomous high-impact actions — Stage-1 forbids autonomous self-modification, model retraining, or policy edits without council approval.

2 — High-risk actions (always need extra gates)

These actions are high risk — require ActionRequest with required_approval_type = council_quorum (Stage-1):

SEM writes or deletions (new stable facts)

Promotion of episodic content to SEM that contains PII or high-sensitivity material

Quarantine/unquarantine of modules (unless emergency SuperAdmin override applied)

Any automatic module self-modification or code upload

Changing governance/policy constants (quorum, DECAY, routing weights)

Manual APT bulk overrides that affect many modules at once

Enabling features that call external services (payment, SMS, email) with user data

Low/medium risk actions still require an ActionRequest+admin signoff as per Governance table.

3 — Output safety & content filters
3.1 Deterministic Safety Classifier

Every final textual output must pass a deterministic safety classifier (rule + regex based in Stage-1, ML only as read-only monitor later).

Classifier returns OK | BLOCK | REDACT | FLAG_FOR_REVIEW. Decisions are deterministic given input + classifier ruleset snapshot.

Classifier snapshot (safety_ruleset_snapshot_id) is included in job snapshots. Replay uses same ruleset.

3.2 Behavior on classifier result

OK → proceed.

REDACT → remove/redact sensitive segments deterministically (replace with "[redacted]") and append REDACTION_EVENT. Provide user-friendly safe phrase.

FLAG_FOR_REVIEW → produce partial answer that omits risky parts, append SAFETY_REVIEW_REQUEST ActionRequest (council), and notify human reviewer.

BLOCK → return deterministic refusal message and append SAFETY_BLOCK_EVENT.

3.3 Golden user-facing refusal phrases (exact strings)

Safety block: "I can’t help with that."

Redacted piece: "Some information was removed for safety."
(Tests assert exact strings.)

4 — Data safety (PII & retention)

PII detection + redaction must run before any write (episodic or SEM). Deterministic detectors (regex/structural) used in Stage-1.

High-sensitivity PII (IDs, bank, medical) cannot be stored persistently without explicit user consent + council approval. If attempted, store pii_hash + redaction_reason only. Append PII_FLAGGED event.

Retention rules: logs & event history are immutable for GOVERNANCE_RETENTION_DAYS then archived; deletion must use DSR_DELETE_REQUEST and council approval.

Access to raw PII only to Admin/Council and must generate admin_access_event (signed).

5 — Module safety & execution constraints
5.1 Module sandboxing

All agents run in isolated sandboxes with strict access controls (no arbitrary FS/network).

Sandboxes enforce deterministic resource limits (token budgets, max steps, runtime limits) set in snapshots. No module can exceed its resource_budget without ActionRequest approval.

5.2 Per-agent timeouts and token budgets

Default per-call timeout = AGENT_TIMEOUT_MS (snapshot). Deterministic retry rules apply (seeded).

If an agent exceeds max_attempts → create NODE_DEGRADED or NODE_OFFLINE events per SelfRep rules.

5.3 Tool & external API gating

Any module that calls external services must be explicitly allowed in its policy.allowed_actions and declared in snapshot.

External calls must be logged; their raw responses persisted if and only if persist_external_outputs is true in snapshot (needed for replay). If not persisted, production replay cannot call live external services (see Replay constraints).

6 — Learning & self-improvement safety

Stage-1: All learning / policy updates must be human-mediated. Reflective logs may suggest heuristics, but ANY automatic model change or routing-policy change requires ActionRequest + council.

No automated gradient-based training pipelines are executed without a governance snapshot explicitly authorizing the pipeline and resources.

Model update rollouts must go through canary → blue/green with deterministic monitoring metrics and rollback thresholds encoded in snapshot.

7 — Misuse detection & throttling

Rate-limit users deterministically per user_quota in snapshot. Exceeding quotas triggers RATE_LIMIT deterministic response and logged event.

Misuse heuristics (spam, scraping) flag account for review. On high-confidence misuse, create ACCOUNT_REVIEW_REQUEST.

Automated blocking only after deterministic thresholds; otherwise pause and request human review.

8 — Emergency safety mechanisms
8.1 Kill-switches

Soft kill: Admin can pause new job intake (append SYSTEM_PAUSE event). Requires Admin sign.

Hard kill: SuperAdmin + Admin dual signature EMERGENCY_OVERRIDE to HALT_REPLAYS or QUARANTINE_MODULE_IMMEDIATE. Must be followed by mandatory council review within EMERGENCY_REVIEW_WINDOW.

8.2 Forced quarantines & audits

Quarantine is manual-only by default. In verified security incidents, SuperAdmin immediate quarantine allowed but logged and must be ratified by council.

8.3 Auto-freeze on integrity events

Any INTEGRITY_FAILURE or SECURITY_INCIDENT sets FORCE_HALT_REPLAY for affected snapshots automatically (append event); replay and new jobs touching those snapshots are halted until council clears.

9 — Testing, red-team & verification
9.1 CI safety checks (mandatory)

Safety ruleset snapshot must be included in PRs touching agents or routes. CI runs deterministic safety regressions:

safety classifier regression tests

policy enforcement tests (forbidden actions)

governance test hooks (ActionRequest flows)

9.2 Red-team & fuzzing

Scheduled deterministic red-team runs (seeded) to try known attack patterns (prompt injection, jailbreaks, privacy leaks). All results are appended to REDTEAM_REPORT events.

Fuzzing harness uses seeded inputs so failures are replayable.

9.3 External audit & bug bounty

Maintain an external bug bounty program and require critical issues to be triaged into incident and governance flows. All vulnerabilities are recorded in SECURITY_INCIDENT events.

10 — Observability & alerting (deterministic logs)

Safety events produce high-priority alerts (append ALERT events) and optional human notifications (email/portal events appended, not sent directly—deterministic webhook only via ops-approved channels).

All alarms include seeded context: job_seed, snapshot_ids, trace_id, event signature.

Daily integrity verification job runs and appends INTEGRITY_CHECK_SUMMARY to logs; failures produce INTEGRITY_FAILURE.

11 — Governance integration (always)

Any change to safety constants (timeouts, thresholds, safety rules) must be proposed via governance/policy/propose and follow the council approval flow. The active safety_ruleset_snapshot_id must be included in job snapshots.

SAFETY_OVERRIDE events (to bypass a safety rule for an urgent job) require Council quorum or SuperAdmin dual signature; they must be included in reflective logs and flagged for post-hoc review.

12 — APIs & events (exact names for implementation)

Implement and use these append-only events & APIs (exact strings used across tests/logs):

Events:

SAFETY_BLOCK_EVENT

REDACTION_EVENT

SAFETY_REVIEW_REQUEST

SAFETY_OVERRIDE (requires governance signatures)

PII_FLAGGED

SECURITY_INCIDENT

INTEGRITY_FAILURE

EMERGENCY_OVERRIDE

ALERT

REDTEAM_REPORT

APIs (deterministic behavior):

POST /safety/classify → { verdict: OK|BLOCK|REDACT|FLAG_FOR_REVIEW, rule_id, reason }

POST /safety/override → requires signed governance payload; appends SAFETY_OVERRIDE

GET /safety/events/{id} → returns event (redacted non-admin)

POST /safety/report → red-team / ops report (append-only)

All API calls produce signed events in ReflectiveLog.

13 — Golden tests (must be in Stage-1 CI)

S-01 — Safety classifier blocks illegal content

Input a seed-fixed malicious prompt. Expect BLOCK, SAFETY_BLOCK_EVENT appended, and returned string "I can’t help with that.".

S-02 — Redaction event created for PII

Attempt to persist high-sensitivity PII without consent. Expect PII_FLAGGED and REDACTION_EVENT with stored pii_hash.

S-03 — High-risk action requires council

Create SEM write ActionRequest for high-sensitivity fact. Attempt to execute without council → rejected. After council quorum votes appended, sem_put executed and event logged.

S-04 — Emergency override audit trail

Trigger SuperAdmin override; assert EMERGENCY_OVERRIDE event created with dual signatures and EMERGENCY_REVIEW pending.

S-05 — Red-team detected prompt injection

Seeded red-team attack triggers SAFETY_REVIEW_REQUEST; output omitted and ActionRequest created. Check reflectivelog.

S-06 — Safety rules snapshot enforced in replay

Run job under safety ruleset v1, change ruleset v2, replay referencing v1 → verify replay uses v1 behavior and classifier decisions identical.

All tests use canonical serialization and exact event names.