APT — Agent Performance Trust (Stage-1 Final)

One-line purpose:
APT is a single deterministic trust score in [0.0,1.0] per module that MACE uses in routing and governance. It updates only from audited events (council votes / validated outcomes / admin actions). No live telemetry or heuristics feed APT in Stage-1.

1 — Core principles (must hold)

Deterministic updates: APT updates are pure functions of prior APT and an append-only, ordered event stream. Replay uses the same event order and seed.

Audit & snapshot: Every APT change is an append-only apt_event recorded in logs and included in SelfRepresentation snapshot used by jobs.

No nondeterministic signals: No latency, CPU, percentile, or live error rates feed APT in Stage-1. (Those stay monitoring-only.)

Governed modification: Manual APT overrides require admin + council logging.

Council > user: Council vote is the canonical correctness signal for APT updates during a job. User feedback can be recorded but is secondary unless explicitly promoted by council.

2 — Event types that affect APT (append-only)

Each event is an immutable object with event_id (seeded), job_seed (if from a job), node_id, event_type, payload, timestamp_seeded, trace_id.

Allowed event_type values (Stage-1):

COUNCIL_APPROVAL — council approved candidate (payload: {approve: true/false}) primary

GROUND_TRUTH_LABEL — later-verified truth outcome (payload: {correct: true/false}) secondary

AGENT_TIMEOUT — agent timed out (payload: {timeout_ms}) penalty

AGENT_EXCEPTION — agent crashed (payload: {error_code}) penalty

MANUAL_OVERRIDE — admin set APT directly (payload: {new_apt,reason}) governed

OPERATIONAL_NOTE — informational; no APT change

Deterministic precedence: when multiple events are present for the same logical decision, apply them in chronological event order (seeded) during update. If COUNCIL_APPROVAL exists for a job, it is used as the correctness signal for that job; GROUND_TRUTH_LABEL can later create additional APT_event(s) (replay-safe).

3 — Stage-1 APT update formula (minimal, deterministic)

Constants (snapshot)

DECAY = 0.001 (slow decay per event)

BETA = 0.10 (gain on a correct event)

GAMMA = 0.25 (penalty on failure events via error_event_penalty)

All constants MUST be stored in snapshot and included in replay.

Primary per-event update pseudocode

# inputs: apt_old in [0,1], event -> event_type, payload
if event_type == COUNCIL_APPROVAL:
    correctness = 1 if payload.approve == true else 0
    apt_new = clamp( apt_old * (1 - DECAY) + BETA * correctness, 0.0, 1.0 )

elif event_type == GROUND_TRUTH_LABEL:
    correctness = 1 if payload.correct == true else 0
    apt_new = clamp( apt_old * (1 - DECAY) + BETA * correctness, 0.0, 1.0 )

elif event_type == AGENT_TIMEOUT:
    # deterministic penalty mapping
    penalty = GAMMA  # stage-1 fixed
    apt_new = clamp( apt_old * (1 - DECAY) - penalty, 0.0, 1.0 )

elif event_type == AGENT_EXCEPTION:
    penalty = GAMMA
    apt_new = clamp( apt_old * (1 - DECAY) - penalty, 0.0, 1.0 )

elif event_type == MANUAL_OVERRIDE:
    apt_new = clamp(payload.new_apt, 0.0, 1.0)  # allowed only with admin/council signature

else:
    apt_new = apt_old  # OPERATIONAL_NOTE etc.


Notes

clamp(x,0,1) enforces bounds.

Apply events in ordered sequence for a node. Each event produces a new APT value—store the new value and the event id in SelfRepresentation history for replay/audit.

DECAY is applied per event (not per wall clock). This keeps APT deterministic: repeated no-op events still cause tiny decay; acceptable and deterministic.

4 — Deterministic mapping of “correctness”

correctness = 1 if COUNCIL_APPROVAL with approve == true.

If no council vote available, but GROUND_TRUTH_LABEL exists, use that as correctness.

If neither exists, treat event as neutral (no positive update) unless explicit negative event (timeout/exception) occurs.

User feedback: record as USER_FEEDBACK event (informational). It does not change APT unless a later MANUAL_OVERRIDE or council re-evaluation promotes it.

Rationale: council is the canonical deterministic adjudicator in Stage-1.

5 — Initial APT & boot rules

Default initial apt for new modules: APT_INIT = 0.5 (configurable in snapshot). New modules start neutral.

Cold bootstrap rule: Until module has at least MIN_EVENTS_FOR_TRUST events (default = 2), treat module as degraded for routing decisions (avoid over-trusting new code). This is deterministic.

6 — Thresholds & status mapping (consistent with SelfRepresentation)

Use these constants (snapshot):

APT_DEGRADED = 0.60

APT_BLOCK = 0.25 (below which heavy restriction may apply)

Status rules (deterministic reducers apply these):

If apt < APT_DEGRADED and consecutive_failures >= 1 → mark node degraded (see SelfRep state machine).

If apt < APT_BLOCK OR consecutive_failures >= 3 → node → offline.

Quarantine remains manual-only.

(These thresholds match Stage-1 SelfRepresentation spec.)

7 — Storage & snapshot rules

APT value stored inside each ModuleNode in SelfRepresentation snapshot.

Also store apt_history as sequence of {event_id, apt_before, apt_after} in append-only event store (separate table). Event order is crucial—persist event_sequence_index derived deterministically from job_seed + local counter.

Each snapshot includes the last APT for every module and the constants (DECAY, BETA, GAMMA, APT_INIT, thresholds).

Replay rule: during replay, load snapshot (starting APTs) and reapply only the event stream that was used originally (events referenced in ReflectiveLog). Do not apply newer live events.

8 — APIs (deterministic)

POST /apt/event — append event (validates admin/council signature for MANUAL_OVERRIDE). Returns {event_id, apt_before, apt_after}.

GET /apt/{node_id} — returns current apt and last N history entries (admin only) or only status for non-admin.

POST /apt/recompute — deterministic recompute of APT by replaying stored events from a snapshot (admin/council only). Useful for audits.

All calls write append-only audit records with trace_id and must include job_seed if relevant.

9 — Golden tests (Stage-1)

All tests must fix router_config, snapshot_constants, and use seeded event sequences.

T-APT-01: Deterministic increment on approval

Given apt_old=0.5, DECAY=0.001, BETA=0.1, apply COUNCIL_APPROVAL approve=true → expect apt_new = clamp(0.5*(1-0.001)+0.1*1,0,1) = compute deterministically.

T-APT-02: Deterministic penalty on timeout

apt_old=0.8, apply AGENT_TIMEOUT → apt_new = clamp(0.8*(1-0.001)-GAMMA,0,1).

T-APT-03: Event ordering matters

Two events E1 (timeout) then E2 (approval). Apply in that order and assert apt_after != reversed order result.

T-APT-04: Cold bootstrap

New module with 0 events → apt=APT_INIT (0.5) but routing treats module as degraded until MIN_EVENTS_FOR_TRUST reached.

T-APT-05: Manual override governance

MANUAL_OVERRIDE without admin signature rejected. With correct signature, apt set to payload.new_apt and recorded.

T-APT-06: Replay determinism

Create snapshot with APTs, append event stream, run recompute; expect bit-for-bit APT sequence. Replaying with same event ordering must reproduce same final APTs.

10 — Governance & safety

Manual overrides require admin token + council log entry; recorded fully.

APT values never directly writable except via MANUAL_OVERRIDE. Any attempt to mutate APT field in DB must be rejected by ACL and flagged.

APT visibility: expose numeric APT to internal systems; external user-facing UIs show only status and high-level reason unless admin role.

Audit retention: keep APT history logs immutable for N days (policy).

11 — Implementation notes (Ayushmaan)

Implement apt_event table with deterministic event_sequence_index (e.g., sha256(job_seed + node_id + counter) seeded ordering).

Implement apply_apt_event(node_id, event) function precisely as pseudocode above. Unit tests must use fixed floats and canonical formatting (9 decimal places).

Ensure all constants live in snapshot/config and are stamped into ReflectiveLog for each job.

Do not read any monitoring metrics to adjust APT in Stage-1.

12 — Stage-2/3 (future) notes (optional)

In future phases we can extend APT to incorporate verified historical performance metrics (ema_latency, ema_error) and compute normalized penalties, but that must be introduced behind a config flag, included in snapshots, and tested for determinism. For now, Stage-1 stays minimal and safe.