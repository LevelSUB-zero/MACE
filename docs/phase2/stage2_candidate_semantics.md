# CANDIDATE ONTOLOGY & SEMANTICS (AUTHORITATIVE)

> **The Core Idea:**
> A Candidate is not a belief. It is a question posed to governance.

---

## C. CANDIDATE ONTOLOGY (WHAT A CANDIDATE REALLY IS)

### C.1 Ontological Status
A Candidate is:
- A compressed hypothesis
- Derived from patterns in episodic memory
- Intended for governance evaluation
- **Not a belief**

Candidates do not assert truth.
They ask:
> “If we had to decide later, what would we consider?”

### C.2 Candidate Lifecycle

1. **Episodic Data Accumulates**: Raw events are logged (Stage-1).
2. **Deterministic Clustering**: Patterns are detected without judgment.
3. **Candidate Formed**: A candidate object is instantiated.
4. **Candidate Judged**: Council applies labels (Truth/Safety/Utility).
5. **Candidate Resolved**:
   - **Ignored**: Not useful or safe.
   - **Rejected**: Explicitly unsafe or untrue.
   - **Conditionally Approved**: Sent to Stage-3 for consolidation (future).
6. **Expiration**: Candidate expires or is superseded.

Candidates **do not persist as memory** in Stage-2.
They are transient evaluation units.

### C.3 Candidate Feature Semantics (Deep & Frozen)
Each feature answers a specific epistemic question. These are fixed and frozen.

| Feature | Question | Semantics |
| :--- | :--- | :--- |
| `frequency` | “Is this recurring?” | Count of identical or near-identical episodic traces. |
| `consistency` | “Is this stable?” | Measure of contradiction over time. |
| `recency` | “Is this current?” | Time-decayed relevance score. |
| `source_diversity` | “Is this echoed?” | Count of distinct agents/sources reporting this. |
| `semantic_novelty` | “Is this new?” | Inverse similarity to existing long-term memories. |
| `governance_conflict_flag`| “Is this allowed?” | Boolean flag if any heuristic rule is triggered. |

**No feature may:**
- Summarize another feature
- Adapt its meaning
- Incorporate learned weights from models

### C.4 Explicit Prohibitions
The following strictly forbidden in candidate construction:
- **Heuristics**: No "magic numbers" or hard-coded rules inside the candidate object itself.
- **Adaptive Thresholds**: Definition of "candidate" cannot change based on load.
- **Live Metrics**: Cannot use real-time system health to boost candidate score.
- **Confidence-as-Truth**: A high confidence score in extraction does not equal truth.

---

## D. ACCEPTANCE CRITERIA
- A candidate can never be mistaken for a committed truth.
- Feature creep is impossible without documentation change.
