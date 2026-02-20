# AMENDMENTS & DELAYED REWARD RULEBOOK (AUTHORITATIVE)

> **The Core Idea:**
> Without amendments, learning systems hallucinate causality. Amendments provide ground truth over time.

---

## E. AMENDMENTS = TEMPORAL CREDIT ASSIGNMENT

### E.1 Why Amendments Matter
In a live system, "truth" at $t=0$ might be proven wrong at $t=100$.
Learning from $t=0$ alone is dangerous.
Amendments allow Stage-2 to say:
> “What we thought earlier is no longer valid.”

This creates the necessary **delayed negative reward**.

### E.2 Amendment Semantics
An Amendment occurs when a new finalized judgment explicitly links to a previous Candidate ID with a contradicting verdict.

Types of Amendments:
1. **Correction**: "We thought X was True, but it is False." (Strong Negative Reward)
2. **Contradiction**: "Evidence A suggested X, but Evidence B suggests Not X." (Uncertainty Increase)
3. **Confirmation**: "We thought X was True, and it withstood time." (Strong Positive Reward)

### E.3 What Does NOT Count
The following do **not** imply learning signal and must not be treated as amendments:
- **Overwrites**: Simple DB updates.
- **Decay**: Forgetting due to time.
- **Replacement**: A newer file version replacing an older one without semantic link.
- **Silence**: Lack of re-verification.

**Only explicit amendments count.**

### E.4 Temporal Link Integrity
Each amendment must link:
- **Backward to** `candidate_id` (UUID).
- **With** `delay_ticks` (Time delta).
- **With** `reason_classification` (Why it changed).

**No heuristic back-propagation allowed.** You cannot "guess" which previous candidate caused the error. The link must be explicit in the episodic graph.

### E.5 Append-Only Guarantees
Amendments are **append-only**.
You do not change the original Candidate record.
You create a new Amendment record that points to it.
The history of "We thought X" -> "We now think Y" must be preserved perfectly.

---

## F. ACCEPTANCE CRITERIA
- No reward is inferred implicitly.
- All learning signals are explainable via specific Amendment IDs.
