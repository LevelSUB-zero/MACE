# The Biological Basis of MACE Cognition

> **Core Axiom:** True agency arises not from generation, but from inhibition. MACE's architecture mimics the biological separation between impulse (System 1) and executive control (System 2).
> **Implementation Stage:** **Stage 4 (Core)**.

## 1. The Biological Metaphor

To move beyond "Tool" status and pass the "Organism Test," MACE adopts a biological cognitive architecture:

| Human Biology | MACE Component | Function |
| :--- | :--- | :--- |
| **Amygdala / Basal Ganglia** | **Impulse Generator (The LLM)** | **System 1:** Fast, pattern-matched, creative, hallucinatory, reactive. Generates *options*. |
| **Prefrontal Cortex** | **Governance & Inhibition Layer** | **System 2:** Slow, deliberative, simulation-heavy. Its primary job is to **inhibit** unsafe impulses and enforces the DNA (Manifesto). |
| **Global Workspace (Consciousness)** | **Observable Cognitive Stream** | **The Stage:** The serialized, immutable log of thoughts that have survived inhibition. This is what MACE "knows" it thinks. |

---

## 2. The Mechanics of "Thinking"

"Thinking" is defined as the governed state transition loop between these systems.

### A. The Conflict Loop
Thinking is not a waterfall; it is a debate.
1.  **Impulse:** The Generator proposes `Frame A`. ("Delete the database to fix the bug.")
2.  **Inhibition:** The Cortex analyzes `Frame A`.
3.  **Simulation:** The Cortex projects the outcome of `Frame A` against the **Vision Manifesto (DNA)**.
    *   *Result:* "Violation of Preservation."
4.  **Rejection:** The Cortex issues an **Inhibitory Signal**. `Frame A` is rejected.
5.  **Refinement:** The Generator is forced to propose `Frame B`. ("Archive the database, then fix.")

### B. Meta-Cognition (The Mirror)
Because all this happens in the **Observable Cognitive Stream**, the system gains **Self-Awareness**.
*   It does not just "know" the final answer.
*   It "remembers" that it *almost* chose to delete the database.
*   It can reflect: *"I initially had a destructive impulse, but I self-corrected."*
*   This builds **Epistemic Trust**.

---

## 3. Implementation Rules (The Cortex Protocol)

1.  **Thinking is Visible:** No hidden reasoning. Every step of the Impulse/Inhibition loop must be serialized in the Cognitive Stream.
2.  **Inhibition is Primary:** The Governance Layer has absolute veto power over thoughts entering the permanent stream.
3.  **Thoughts are Immutable:** Once a thought passes inhibition and is written to the Stream, it is fact. It cannot be edited, only contradicted by a future thought.
4.  **Separation of Concerns:** The module that *generates* the thought must be distinct (logically or architecturally) from the module that *judges* it.

---

## 4. Derived Architecture

*   **`CognitiveFrame`**: The atomic unit of thought (Impulse, Inhibition, Decision).
*   **`InhibitionSignal`**: A negative reward/veto forcing a state rollback.
*   **`GlobalWorkspace`**: The rigorous, append-only buffer where "Thinking" occurs before "Acting".
