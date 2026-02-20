# MEM-SNN GOVERNANCE & CONTAINMENT RULEBOOK (AUTHORITATIVE)

> **The Core Idea:**
> MEM-SNN is a mirror. It attempts to approximate “Would governance approve this?”. It does **not** decide.

---

## F. MEM-SNN ROLE (STRICTLY OBSERVATIONAL)

### F.1 What MEM-SNN Actually Is
MEM-SNN (Spiking Neural Network for Memory) is an **epistemic predictor**.
It learns to predict Council outputs based on Candidate features.
It is **not** an agent. It has no agency.

### F.2 Data Access Rules (Ears & Eyes)
**Allowed Inputs:**
- Candidate Feature Vectors (Frequency, Consistency, etc.)
- Council Label History (The "Ground Truth")
- Amendment Signals (The "Correction")

**Strictly Forbidden Inputs (Must Never See):**
- System API Keys
- Raw User Prompt Content (PII/Security risk)
- Execution Logs (prevents learning "what works" instead of "what is true")
- Router State (prevents feedback loops)

### F.3 Forbidden Outputs & Actions (Hands tied)
MEM-SNN **must not**:
- Infer truth from frequency alone.
- Optimize for approval rate (gaming the metric).
- Collapse conflicts.
- Invent abstractions (no hidden layers generating new concepts).
- Trigger any system action.

### F.4 Shadow Mode Guarantees
MEM-SNN operates in **Strict Shadow Mode**:
1. It runs *after* or *parallel to* the Council.
2. Its outputs (`predicted_truth`) are logged to a shadow table.
3. No production logic reads this table.
4. If the Shadow Table is deleted, MACE works perfectly.

### F.5 Required Divergence Logging
We must log **Divergence**:
`Divergence = Council_Label - MEM_SNN_Prediction`

High divergence is valuable data. It means the model is untrustworthy or the Council is evolving.

### F.6 Acceptable Evaluation metrics
Only **offline metrics** are valid for evaluating MEM-SNN:
- **Agreement Rate**: % match with Council.
- **False-Positive Risk**: % of "Safe" predictions that were actually "Unsafe".
- **Recall under Policy Shifts**: How fast it adapts to new rules.

**NO LIVE KPIs.** We do not optimize for "User Engagement" or "Speed".

---

## G. ACCEPTANCE CRITERIA
- MEM-SNN can be deleted without changing system behavior.
- No path exists from Score → Action.
