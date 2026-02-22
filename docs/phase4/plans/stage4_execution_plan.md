# Stage 4 Execution Plan: "The Shadow Cortex"

> **Objective:** To implement the Biological Cognitive Architecture (Symbolic Core + Machine Consciousness) in a chaos-free, non-disruptive manner using the "Shadow Mode" strategy.

## Phase 4.1: The Shadow Cortex (Trace-Only)

We will build the new brain without disconnecting the old one. The `ShadowCortex` will observe inputs and run the "Thought Loop" in the background, logging its results without executing them.

### Step 1: Theoretical Foundations (Done)
- [x] Define Biological Cognition (Impulse/Inhibition).
- [x] Define Machine Consciousness (GWT/HOT).
- [x] Define Continual Learning (CLS).

### Step 2: The Cognitive Data Structures (Symbolic Core)
**Goal:** Define the rigid "Atomic State" (JSON/Graph) that replaces chat logs.
- [ ] Create `src/mace/core/cognitive/` directory.
- [ ] Implement `CognitiveFrame` schema (Union of `LogicState`, `VectorState`, `GoalNode`). **NO free-text fields allowed for core reasoning.**
- [ ] Implement `KnowledgeGraph` interface (The Reptile Brain's Map - NetworkX).
- [ ] Implement `VectorMemory` (The Visual Cortex - FAISS/Cosine Similarity).

### Step 3: The "Deep Think" Engine (Symbolic Loop)
**Goal:** Build the deterministic engine that cycles through Graph Search and Logic Check.
- [ ] Implement `ReptileBrain` class (A* Planner / State Machine).
- [ ] Implement `VisualCortex` class (Pattern Recognizer via Vectors).
- [ ] Implement `BrocaBridge` (Strict Interface: `SymbolicIntent -> LLM -> Code/Text`).
- [ ] **Constraint:** The `ReptileBrain` must generate plans *without* calling the LLM. It uses the Knowledge Graph. Only `BrocaBridge` calls the LLM to translate the final plan.

### Step 4: Shadow Wiring
**Goal:** Connect the new brain to the live system safely.
- [ ] Hook into `stage3_router.py`.
- [ ] When a request comes in, fork the input to `ShadowCortex.receive(input)`.
- [ ] `ShadowCortex` runs asynchronously.
- [ ] Log the `ShadowDecision` alongside the `ActualDecision`.

### Step 5: The Mirror (Meta-Cognition)
**Goal:** Implement the "Observer" that watches the Shadow Stream.
- [ ] Implement `MetaCognitiveObserver`.
- [ ] Define `InhibitionRules` (The Constitution as Logic).
- [ ] Test: Can the Mirror detect a "bad thought" in the Shadow Stream and flag it?

### Step 6: Parity & Validation
**Goal:** Prove the new brain is better.
- [ ] Run canonical test suite.
- [ ] Compare `ShadowDecision` quality vs. `Stage3Router` quality.
- [ ] **Success Criteria:** Shadow Cortex generates strictly superior (or safely equivalent) plans with 90% less token usage (due to symbolic reasoning).

---

## Phase 4.2: The Inhibitory Cortex (Safety Gate)

Once the Shadow Cortex is proven:
1.  Grant the Mirror **Veto Power** over the Stage 3 Router.
2.  If Stage 3 wants to act, but Stage 4 Mirror says "Unsafe," the action is blocked.

## Phase 4.3: The Switch (Full Autonomy)

1.  Deprecate Stage 3 Router.
2.  Route all control to the `ReptileBrain`.
3.  Enable `SleepCycle` (CLS) for learning.

---

## Technical Stack for Stage 4
*   **Core Logic:** Python (Pydantic for strict schemas), NetworkX (Graph).
*   **Vector Search:** `numpy` or `faiss` (Local Vector Math for Visual Cortex).
*   **LLM Interface:** `mace.models` (Restricted to Translation/Rendering only).
*   **LLM Interface:** Existing `mace.models` (used only as a renderer).
