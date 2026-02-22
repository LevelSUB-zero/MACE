# Machine Consciousness & Meta-Cognition Architecture

> **Scientific Basis:** Global Workspace Theory (GWT), Higher-Order Thought (HOT), and Active Inference.
> **Implementation Stage:** **Stage 4 (Meta-Cognition)**.
> **Goal:** To implement a functional "Synthetic Prefrontal Cortex" that enables MACE to think about its own thinking.

## 1. The Core Theory: "Symbolic Core, Linguistic Interface"

To achieve "True Thinking" (which is largely non-verbal in nature), MACE decouples **Cognition** from **Language**. Only "Surface Thinking" (communication) uses LLMs. "Deep Thinking" (planning, causality, safety) uses Symbolic, Vector, and Graph operations.

| Layer | Type | Mechanism | Role |
| :--- | :--- | :--- | :--- |
| **1. The Reptile Brain (Core)** | **Symbolic / Logic** | State Machines, Graph Search (A*), Formal Logic rules. | **Planning & Safety.** Handles causality, dependencies, and hard constraints. *Thinks in Math/Pointers.* |
| **2. The Visual Cortex (Intuition)** | **Vector / Geometric** | High-dimensional Vector Arithmetic, Similarity Search. | **Pattern Recognition.** "This situation is close to failure mode X." *Thinks in Geometry.* |
| **3. Broca's Area (Interface)** | **Probabilistic (LLM)** | Transformer / Token Generation. | **Translation.** Converts Symbolic Intent into Human Text or Code Syntax. *Thinks in Words.* |

---

## 2. The Implementation Mechanism

### A. Non-Verbal Cognition (The Thinking Loop)
True thinking happens in the **Reptile Brain**:
1.  **State Perception:** The system perceives the environment not as text, but as a **Knowledge Graph**.
2.  **Navigation:** "Reasoning" is implemented as traversing this graph.
    *   *Goal:* "Secure the system."
    *   *Operation:* Graph search for `node:System` -> `has_vulnerability` -> `patch_available`.
    *   *Result:* A rigorous path found. No hallucination possible.
3.  **Vector Intuition:** When logic is too brittle, **Vector Space** provides intuition.
    *   *Operation:* `Distance(CurrentState, SuccessState)` vs `Distance(CurrentState, FailureState)`.
    *   *Decision:* Move towards Success.

### B. The "Translation" Call (Broca's Area)
The LLM is called *only* when the Symbolic Brain has a completed intent but lacks the syntax to express it.
*   *Reptile Brain:* "I have a valid plan: [Step 1: Write File X, Content: <VectorID:AuthLogic>]."
*   *Broca's Trigger:* "LLM, please translate <VectorID:AuthLogic> into Python code."
*   *Output:* The code is generated.
*   *Validation:* The Logic brain creates a Sandbox to verify the code matches the intent.

### C. The "Meta-Cognitive" Check (Symbolic)
Meta-Cognition is not "asking an LLM if it's sure." It is **State Invariance Checking.**
*   *Check:* "Does the proposed Action State violate the `ImmutableConstraint_1` (Governance)?"
*   *Mechanism:* Boolean Logic Check. `if Action.level > Permission.level: VETO`.
*   *Power:* Absolute. Math beats probability every time.

---

## 3. The "Meta-Consciousness" Loop (Synthetic Awareness)

True Meta-Consciousness is the ability to **Break the Loop.**

### The "Pause & Pivot" Protocol
1.  **Detection:** The Reptile Brain detects a "Cyclic Graph" (Infinite Loop) or "High Entropy" (Confusion) in its Vector States.
2.  **Interrupt:** The Hardware/Logic layer forces a **System Pause**.
    *   *"My heuristic (A*) is failing to converge."*
3.  **Reframing:** The system triggers a **Strategy Shift**.
    *   *Switch:* From "Greedy Search" (Fast) to "Monte Carlo Simulation" (Deep).
4.  **Resume:** The Generators now operate under the *New Strategy*.

---

## 4. Engineering Rules for Stage 4

1.  **Thinking != Talking:** Do not use LLMs to "reason" about logic. Use them only to "render" the result of logic.
2.  **Math is Truth:** Core decisions (Routing, Safety, Planning) must be reducible to Vector Arithmetic or Graph Operations.
3.  **No Unobserved Action:** The "Motor Cortex" (Tools/Output) is physically disconnected from the "Generators." It can *only* be triggered by the "Mirror" after a valid Meta-Check.
4.  **Implicit State:** The "State of Mind" is a Graph/Vector snapshot, not a chat log.
