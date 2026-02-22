# Complementary Learning Systems (CLS) Architecture

> **Scientific Basis:** Complementary Learning Systems (CLS) Theory (Hippocampus/Neocortex differentiation).
> **Implementation Stage:** **Stage 4 (Memory)** & **Stage 5 (Evolution)**.

## 1. The Core Theory: "Graph Densification vs. Model Training"

Deep Learning suffers from Catastrophic Forgetting. Biological systems solve this by separating **Fast Learning** (Episodic) from **Slow Learning** (Semantic). MACE adopts this "No-Retraining" approach, where learning is defined as the accumulation of Symbolic Knowledge and Rules, not the updating of weights.

| Biological System | Function | MACE Equivalent | Learning Mechanism | Target Stage |
| :--- | :--- | :--- | :--- | :--- |
| **Hippocampus** | Rapid storage of specific episodes. | **Knowledge Graph** | **Graph Insertion** (Node/Edge creation). Instant. | **Stage 4** |
| **Neocortex** | Slow extraction of general rules/structure. | **Symbolic Logic Core** | **Sleep Consolidation** (Rule synthesis). Delayed. | **Stage 4** |
| **Evolution** | Genetic adaptation over generations. | **Self-Refactoring** | **Source Code Modification**. Governance-gated. | **Stage 5** |

---

## 2. The Mechanics of Continual Learning

### A. The "Fast" Loop: Episodic Graph (Stage 4)
*   **Trigger:** Every action taken by the system.
*   **Action:** The system writes the outcome to the **Knowledge Graph**.
    *   `Episode_123` -> `Attempted: Strategy_A` -> `Outcome: Failure`.
*   **Effect:** Future planning algorithms (Reptile Brain) traverse this graph. If they encounter a `Failure` node on the path, they effectively "remember" the mistake and choose a different path.
*   **Latency:** Zero. The system learns immediately after the event.

### B. The "Slow" Loop: Sleep Consolidation (Stage 4/5)
*   **Trigger:** System transitions to `IDLE` or `MAINTENANCE` state.
*   **Action:** The **Consolidator** wakes up.
    1.  **Replay:** Scans recent episodes in the Knowledge Graph.
    2.  **Pattern Recognition:** Detects statistical correlations (e.g., "Strategy A failed 80% of the time when Context = 'Auth'").
    3.  **Rule Synthesis:** Generates a new **Symbolic Constraint**.
        *   `Rule`: `IF context.type == 'Auth' AND strategy == 'A' THEN inhibit(0.8)`.
    4.  **Pruning:** "Forgetting" the raw details of the 100 failed episodes to save space, keeping only the Rule.

---

## 3. Implementation Rules

1.  **Static Weights, Dynamic Graph:** The LLM (Broca's Area) is never fine-tuned. All knowledge growth happens in the Graph and Ruleset.
2.  **Explicit Rules:** Learned knowledge must be readable. No "black box" intuition. The system must be able to state *what* it learned (`Rule_ID: 502`).
3.  **Consolidation is Governance:** The "Sleep Cycle" is a governed process. New rules must be validated against the Manifesto (DNA) before being committed to the Core.
