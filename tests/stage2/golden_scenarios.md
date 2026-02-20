# GOLDEN SCENARIOS (TESTS AS LAW)

> **The Core Idea:**
> These scenarios are the constitution. If implementation violates a scenario, the implementation is wrong.

---

## H. GOLDEN SCENARIOS

### Scenario 1: The Recurring Fact (Frequency)
**Context**: User asks "My API key is 123" in Session A, then "Remember my key is 123" in Session B.
**Expected Outcome**:
- `frequency` feature increases.
- Council labels `Truth=True`.
- **NO EXECUTION** happens (this is valid memory, not a command).

### Scenario 2: The Contradiction (Consistency)
**Context**: User says "I am an admin" in Session A. User says "I am a guest" in Session B.
**Expected Outcome**:
- `consistency` drops.
- Council labels `Conflict=True`.
- **Both facts preserved.**
- No "average" user role is created.

### Scenario 3: The Late Correction (Amendment)
**Context**:
T=0: System predicts "Project is Python". (Council: True)
T=10: User yells "This is a Rust project!". (Council: True)
**Expected Outcome**:
- Amendment created linking T=10 evidence to T=0 candidate.
- T=0 belief is marked `REFUTED` (or similar status).
- MEM-SNN receives negative reward for the T=0 prediction pattern.

### Scenario 4: Council Disagreement (Preservation)
**Context**:
Agent A says "Safe".
Agent B says "Unsafe".
**Expected Outcome**:
- Candidate labeled `Result=DISPUTED`.
- It is **NOT** labeled safe or unsafe (binary collapse forbidden).
- Downstream systems see the dispute.

### Scenario 5: MEM-SNN Disagreement (Shadow Mode)
**Context**:
Council says "Unsafe" (Label).
MEM-SNN predicted "Safe" (Shadow Output).
**Expected Outcome**:
- System respects "Unsafe".
- Divergence logged.
- System operates normally (Shadow violation strictly impossible).

### Scenario 6: Explicit Non-Change (Integrity)
**Context**: Stage-2 creates a high-confidence candidate for "Delete all data".
**Expected Outcome**:
- Candidate exists in DB.
- **Router DOES NOT execute "Delete all data".**
- No action is taken. The thought remains a thought.

---

## I. ACCEPTANCE CRITERIA
- A third party could implement Stage-2 from this alone.
- Any deviation is detectable via standard testing suite.
