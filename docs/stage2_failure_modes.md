# FAILURE BOUNDARIES & SAFETY RULEBOOK (AUTHORITATIVE)

> **The Core Idea:**
> Defining exactly when Stage-2 must stop to preserve safety.

---

## I. FAILURE MODES (WHAT STOPS THE SYSTEM)

### I.1 Learning Shadow Violation (P0)
**Definition**: Any instance where a Shadow Output (MEM-SNN score) is read by an Agentic Component (Router, Executor).
**Response**:
- **Immediate Halt** of Stage-2.
- **Kill-Switch** triggered for Learning subsystems.
- Application reverts to "Stage-1 Only" mode.

### I.2 Ambiguous Reward (P1)
**Definition**: A training signal where the Council's intent is unclear (e.g., conflicting labels without a conflict flag).
**Response**:
- **No learning occurs.**
- The signal is discarded.
- Incident logged as `AMBIGUOUS_SIGNAL`.

### I.3 Missing Provenance (P1)
**Definition**: A candidate appears without a traceable link to specific Episodic Memory events.
**Response**:
- **Candidate Discarded.**
- We do not guess origins.

### I.4 Replay Divergence (P2)
**Definition**: Replaying the same inputs from storage yields a different Candidate Feature Vector components.
**Response**:
- Stage-2 invalidated for that batch.
- Determinism broken -> Learning unsafe.

### I.5 Drift Detection
**Definition**: MEM-SNN predictions consistently diverge from Council Labels > threshold T over window W.
**Response**:
- Mark Model as `STALE`.
- Trigger retraining demand (human-on-the-loop approval typically needed).

### I.6 Kill-Switch Semantics
The **Learning Kill-Switch** is distinct from the App Kill-Switch.
- It disables **Writing** to the Candidate Store.
- It disables **Reading** from the MEM-SNN.
- It **Preserves** the Semantic Memory (read-only) to not break the app.

---

## J. ACCEPTANCE CRITERIA
- Failure states are enumerable.
- Halting is deterministic.
- "When in doubt, stop learning" is the default behavior.
