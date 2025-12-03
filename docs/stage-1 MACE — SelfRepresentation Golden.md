✅ MACE — SelfRepresentation Golden Rules (Stage-1 Final Version)

SelfRepresentation is MACE’s structural self-model — a deterministic graph of modules and their health, trust (APT), and dependencies.
It must be bit-for-bit replayable, append-only, and governance controlled.

This version is minimal but complete, exactly matching your ideology and current architecture.

1 — Core Principles (Unbreakable Laws)

Deterministic:
All fields used in workflow decisions MUST be deterministic and replayable.
No nondeterministic data (CPU %, RAM, live performance metrics) may influence routing.

Snapshot-based:
Every job uses a SelfRepresentation snapshot stored inside its ReflectiveLog.

Append-only events:
Modules never mutate silently.
All updates occur through append-only “module_state_events”.

Strict schema:
Only fields defined in the spec are allowed.
No hidden / dynamic fields.

Governance-controlled:
Registration, quarantine, and policy changes require Council or Admin signatures.

No ML inference in routing yet:
Stage-1 uses pure rule-based logic only.

2 — Canonical Module Schema (Minimal, Deterministic)
{
  "node_id": "agent:logic_v1",
  "type": "agent|tool|service|router|adapter|memory",
  "display_name": "Logic Agent",
  "version": "1.0.0",

  "status": "healthy",  // healthy | degraded | offline | quarantined
  "status_reason": null,

  "apt": 0.87,          // Agent Performance Trust [0.0, 1.0]

  "metrics": {
    "consecutive_failures": 0,
    "total_calls": 1234
  },

  "dependencies": ["service:sem_store"],

  "policy": {
    "allowed_actions": ["read_sem"],
    "forbidden_actions": ["write_sem", "self_modify"]
  },

  "registration": {
    "registered_by": "admin",
    "registered_at": "2025-11-29T11:59:00Z"
  },

  "last_updated": "2025-11-29T12:00:00Z"
}

Notes

Removed: cpu_pct, mem_mb, latency, error rates → NOT allowed in Stage-1 (nondeterministic).

Only deterministic counters remain.

3 — Canonical Dependency Schema (Minimal)
{
  "edge_id": "agent:logic_v1->service:sem_store",
  "from": "agent:logic_v1",
  "to": "service:sem_store",
  "required": true
}

Notes:

No latency or runtime metrics.

Only structural dependency.

4 — APT Update Rules (Deterministic, Minimal)

Stage-1 uses the simplest stable deterministic APT update.

Let:

apt_old be previous trust

correctness ∈ {1,0} (based on result validation by Council)

decay = 0.001

beta = 0.1

Formula:

apt_new = clamp(apt_old * (1 - decay) + beta * correctness, 0.0, 1.0)


APT only increases when an agent is correct.
APT declines slowly over time.

No latency, no error rate, no non-deterministic signals.

5 — Status State Machine (Stage-1 Minimal)

States:
healthy → degraded → offline → quarantined

Deterministic transitions:
healthy → degraded
if apt < 0.6
OR consecutive_failures >= 1

degraded → offline
consecutive_failures >= 3

offline → quarantined
MANUAL ONLY (admin or council)

degraded → healthy
consecutive_failures == 0 AND apt >= 0.6

Notes:

This is minimal, deterministic, replay-safe.

BrainState does NOT directly modify module status.

6 — Failure Propagation Rules (Minimal, Deterministic)

Instead of inflating metrics, we only set a flag.

If any required dependency is not healthy:

dependency_unhealthy = true


Router uses this boolean to reduce availability score.

No numbers, no dynamic effects — pure rule logic.

7 — Router Availability Score (Stage-1)

Deterministic formula:

availability_score = apt * status_weight


Where:

status_weight = {
  healthy: 1.0,
  degraded: 0.6,
  offline: 0.0,
  quarantined: 0.0
}


If dependency_unhealthy = true:

availability_score *= 0.5


Simple, predictable, replayable.

8 — Snapshot Rules

Snapshot is created before job execution.

Snapshot includes:

all modules

all edges

all APT values

all statuses

all policies

router thresholds

config hash

schema version

Snapshot ID stored in ReflectiveLog.

Replay uses the same snapshot ID.

9 — Governance / Safety Golden Rules

Quarantine = manual only
No auto-quarantine under any circumstances.

Module registration requires:

admin signature

hashed immutable fields

policy validation

Forbidden actions:

modules cannot self-modify

cannot modify policies

cannot modify dependencies

cannot modify APT

cannot modify SelfRepresentation

Council override needed for:

quarantining

unquarantining

changing module policies

adding modules with SEM-write permission

10 — Golden Test Scenarios (Stage-1 Minimal)
T-SR-01: Registration deterministic

Register a module

Hash stable

Snapshot stable

Replay identical.

T-SR-02: APT update deterministic

For a given sequence of correctness signals, APT must match expected vector exactly.

T-SR-03: Status transitions

apt < 0.6 → degraded

3 failures → offline

offline → quarantined only by admin.

T-SR-04: Dependency flag

If dependency offline → dependency_unhealthy = true.

T-SR-05: Router availability score

Must match exact deterministic formula.

T-SR-06: Replay equality

Snapshot must produce identical routing decisions across replays.

T-SR-07: Forbidden actions blocked

Non-admin attempt to modify module → PERMISSION_DENIED.