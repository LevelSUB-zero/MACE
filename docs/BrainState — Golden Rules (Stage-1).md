BrainState — Golden Rules (Stage-1)

Purpose (one line)
BrainState is MACE’s runtime cognitive state: goals, working memory (WM), short-term context (CWM), attention/modulators, and reward signals that steer decision depth, routing preferences, and short-horizon planning. It is ephemeral for live runs but fully snapshottable and replayable for any job.

1 — Core principles (must always hold)

Deterministic under job seed: All BrainState updates that affect decisions during a job must be deterministic given the job seed + job inputs. Any pseudo-randomness MUST be seeded from job_seed.

Snapshot & replay: Each job records brainstate_snapshot_id in the ReflectiveLog (created before execution). Replays load that snapshot and produce identical BrainState evolution.

Separation: BrainState = cognitive workspace only. It may read SelfRepresentation and SEM snapshots but must not mutate SelfRepresentation.

Append-only learning hooks: Changes that should persist (e.g., memory promotions, APT updates) must be written as explicit events separate from BrainState.

Governed effectors: Any BrainState-driven action that affects persistent state (SEM writes, module registration requests, hires/calls to admin) requires council or admin gating per policy.

2 — Canonical BrainState schema (minimal)
{
  "brainstate_id": "bs:<job_seed>:<timestamp>",
  "job_seed": "seed-xxxx",
  "timestamp": "2025-11-29T12:00:00Z",
  "goals": [
    {
      "goal_id": "g1",
      "priority": 0.8,
      "type": "answer|clarify|save|verify|plan",
      "status": "active|succeeded|failed|paused",
      "created_at": "...",
      "deadline_ts": "...",        // optional
      "origin": "user|system|agent",
      "metadata": { }
    }
  ],
  "WM": [   /* working memory list, newest-first */
    { "wm_id":"w1","type":"fact|context|user_hint","value":"...","ttl_ticks":3, "created_at":"..." }
  ],
  "CWM": {  /* consolidated working memory - short stable context */
    "topic": "quantum_basics",
    "tokens_used": 512
  },
  "attention": {
    "attention_gain": 0.75,    // [0.0,1.0]
    "explore_bias": 0.15,      // [0.0,1.0]
    "reward_signal": 0.6       // [0.0,1.0]
  },
  "resource_budget": {
    "token_budget": 2048,      // deterministic number allocated by policy
    "max_depth_allowed": 2
  },
  "recent_failures": [
    { "node_id":"agent:math_v1","ts":"...","reason":"timeout" }
  ],
  "last_updated": "..."
}


Notes:

All timestamps used for bookkeeping must be derived from job_seed + deterministic offsets if they affect routing/decisions.

WM entries have ttl_ticks (integer) not time durations. A tick is a deterministic step in the workflow.

3 — Key concepts & invariants

Goal priority is deterministic: priority ∈ [0,1] computed from user intent + static heuristics (no ML).

WM vs CWM:

WM = volatile, short-lived items (ttl_ticks).

CWM = short-term consolidated context used for multi-step reasoning (recomputed deterministically from WM when needed).

Attention modulators (attention_gain, explore_bias, reward_signal) determine depth & whether to explore alternate agents or exploit high-APT ones. Values ∈ [0,1].

Resource budget: token_budget and max_depth_allowed are fixed per job snapshot and cannot be changed by BrainState without human/admin/council approval.

BrainState cannot directly write to SEM — writes are done through governance-checked actions.

4 — Deterministic update rules

All updates must be pure functions of prior BrainState, current inputs, and job_seed.

4.1 WM lifecycle (tick-based)

On each reasoning step (tick):

For each wm entry: ttl_ticks -= 1.

Remove WM entries with ttl_ticks <= 0.

Insertion: Agents or the router can append WM entries only via deterministic functions; newly inserted WM entries must include created_at_tick and initial ttl_ticks (default = 3 ticks unless goal-specific override present in snapshot).

Promotion to CWM: If an item is referenced ≥ PROMOTION_REFERENCES times within PROMOTION_WINDOW ticks (both integers in snapshot), promote to CWM via deterministic consolidation rule.

Default constants (Stage-1):

DEFAULT_WM_TTL = 3 ticks

PROMOTION_REFERENCES = 2

PROMOTION_WINDOW = 4 ticks

4.2 CWM maintenance

Recompute CWM only when:

a new goal is created, OR

an item is promoted from WM.

CWM is a deterministic summary: prefer most referenced WM items; ensure token count ≤ resource_budget.token_budget/4 for CWM.

4.3 Attention & explore_bias update

Deterministic update per tick:

reward_signal ∈ [0,1] computed from last council vote or user feedback:
  reward_signal = (council_approval ? 1 : 0) * 0.8 + (user_upvote ? 1 : 0) * 0.2

attention_gain_new = clamp( attention_gain_old * (1 - a_decay) + reward_signal * a_gain, 0,1 )
explore_bias_new = clamp( explore_bias_old * (1 - e_decay) + (1 - reward_signal) * e_gain, 0,1 )


Constants (Stage-1):

a_decay = 0.05, a_gain = 0.25

e_decay = 0.03, e_gain = 0.15

All constants stored in snapshot.

4.4 Reward signal source & determinism

Primary source: immediate Council vote approve boolean (1/0) — deterministic during job because council in Stage-1 is rule-based or stubbed.

Secondary: explicit user feedback captured in-session (1/0).

Combine as above in deterministic weighted sum.

4.5 Goal lifecycle rules (deterministic)

Goal statuses: active, succeeded, failed, paused.

Transitions:

created → active.

active → succeeded when:

required deliverable produced and final_confidence >= CONFIDENCE_THRESHOLD (threshold from snapshot; default 0.7)

active → failed when:

max_attempts_reached (default 3) OR repair loops exhausted.

active → paused when:

resource_budget exhausted OR higher-priority goal preempts (priority difference > 0.2).

Goal priority determination:

priority = clamp( user_priority_weight * user_specified + system_priority_weight * heuristic_score, 0,1 )

Stage-1 defaults: user_priority_weight = 0.8 (user-specified dominates), system_priority_weight = 0.2.

All weights part of snapshot.

5 — Router & BrainState interaction (deterministic heuristics)

Router consults BrainState via POST /brainstate/query returning:

max_depth_allowed = min(snapshot.max_depth_allowed, floor( attention_gain * snapshot.max_depth_allowed ) )

candidate_bias = { prefer_high_APT: attention_gain >= 0.6, allow_explore: explore_bias >= 0.2 }

Router rules:

If attention_gain < 0.2 → force depth = 0 (quick answer only).

If resource_budget.token_budget < snapshot.min_token_threshold → force shallow path.

Router must never exceed snapshot.max_depth_allowed.

All values deterministic.

6 — Persistent decisions & gating

Any action from BrainState that requests persistent change (SEM write, module registration request, policy change) must create an ActionRequest object appended to the ReflectiveLog and flagged for council/admin approval. The request contains:

action_id, origin, payload, justification (derived deterministically), timestamp_seeded.

Only after council_approval == true (logged) will the action be executed.

7 — Privacy & redaction rules

BrainState may hold user-sensitive context in WM or CWM only during the job. Before storing any persistent event referencing sensitive content, PII detector must run. If PII detected, redact sensitive fields in any persistent record (store hash+metadata only) unless explicit user opt-in exists (logged).

BrainState snapshots saved for replay must redact PII for non-admin roles; full snapshots are accessible only to admin/council endpoints.

8 — Snapshot & replay rules for BrainState

Snapshot creation: Before job run, generate brainstate_snapshot containing initial goals, resource_budget, constants, and empty WM/CWM. Snapshot signed and stored; brainstate_snapshot_id saved in ReflectiveLog.

During replay: Load snapshot and deterministic events (council votes, user inputs) to reconstruct BrainState evolution; seeded RNG must use same job_seed.

No live telemetry should be used during replay.

9 — APIs (deterministic behavior)

POST /brainstate/create_snapshot → returns brainstate_snapshot_id

GET /brainstate/{snapshot_id} → snapshot JSON (admin-protected)

POST /brainstate/tick → advances BrainState by one deterministic step given inputs (events, council votes, user feedback). Returns updated BrainState.

POST /brainstate/query → returns derived routing hints: {max_depth_allowed, prefer_high_APT, allow_explore}

All calls append audit entries with trace_id.

10 — Golden test scenarios (must be codified)

T-BS-01 — WM TTL expiry

Setup: create WM entry with ttl_ticks=2. Run two ticks. Expect WM entry removed.

T-BS-02 — Promotion to CWM

Setup: Insert same WM item twice within PROMOTION_WINDOW. After second tick, item promoted to CWM deterministically.

T-BS-03 — Attention & explore update from council vote

Setup: initial attention_gain=0.5. Council approves result (approve=true). After tick, attention_gain increases deterministically per formula.

T-BS-04 — Goal success & failure

Setup: create goal with required deliverable; simulate success meeting confidence threshold → status becomes succeeded. Simulate repeated failures (repair loops) → failed.

T-BS-05 — Router hint generation

Given snapshot with max_depth_allowed=3 and attention_gain=0.4, POST /brainstate/query returns max_depth_allowed = floor(0.4*3)=1.

T-BS-06 — Deterministic replay

Create snapshot, run job with seeded events, capture BrainState trace. Replay with same seed+events → BrainState trace must be bit-for-bit equal.

T-BS-07 — ActionRequest gating

BrainState requests SEM write as action; ensure ActionRequest appended and not executed until council approval logged.

11 — Failure boundaries & safe defaults

Missing constants in snapshot → use safe defaults (documented) and log warning. Example: attention_gain default = 0.5. Warnings are only for ops, do not change decision determinism for replay (snapshot must include constants).

If council absent or stuck → default reward_signal = 0 (conservative).

If user feedback conflicting with council, council outcome used for deterministic reward_signal (council overrides user for that job).

12 — Implementation notes for Ayushmaan

Represent BrainState as Pydantic dataclass with deterministic tick() method.

Deterministic RNG seeded from job_seed only for any randomized tie-breaking. Prefer deterministic tie-breakers (lexicographic).

Keep all constants in snapshot/config; never hardcode in update functions.

Add unit tests T-BS-01..T-BS-07 into CI with seeded runs.

Expose POST /brainstate/tick for executor to call between stages (router -> agent -> council -> brainstate.tick(...)).

Ensure ActionRequests are immutable append-only records in DB.

13 — Governance notes

BrainState snapshots available to admin/council only.

Any persistent learning (memory promotions, policy changes) must go through ActionRequest → Council approval → persistent write.

BrainState itself cannot be modified by non-authorized actors; only reducer via deterministic events can update.

14 — Final alignment statement

This BrainState spec:

Retains Stage-0 determinism & replay invariants.

Gives MACE an explicit, testable cognitive workspace (WM/CWM, goals, attention, reward).

Keeps all decision-relevant values deterministic and snapshot-driven.

Provides clear gating for persistent changes and privacy protection.