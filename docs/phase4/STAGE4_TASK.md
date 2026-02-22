# Stage 4 Task Tracker: The Shadow Cortex & Inhibitory Gate

## Phase 4.1: The Shadow Cortex (Trace-Only) [DONE]
### Step 1: Theoretical Foundations [DONE]
- [x] Define Biological Cognition (Impulse/Inhibition).
- [x] Define Machine Consciousness (GWT/HOT).
- [x] Define Continual Learning (CLS).

### Step 2: The Cognitive Data Structures (Symbolic Core) [DONE]
- [x] Create `src/mace/core/cognitive/` directory.
- [x] Implement `CognitiveFrame` schema.
- [x] Implement `KnowledgeGraph` interface.
- [x] Implement `VectorMemory`.

### Step 3: The "Deep Think" Engine (Symbolic Loop) [DONE]
- [x] Implement `ReptileBrain` class.
- [x] Implement `VisualCortex` class.
- [x] Implement `BrocaBridge`.

### Step 4: Shadow Wiring [DONE]
- [x] Hook into `stage3_router.py`.
- [x] Implement `ShadowCortex` main class.
- [x] Async forking of input.
- [x] Shadow logging.

### Step 5: The Mirror (Meta-Cognition) [DONE]
- [x] Implement `MetaCognitiveObserver`.
- [x] Define `InhibitionRules`.
- [x] Test: Can the Mirror detect a "bad thought"?

### Step 6: Parity & Validation [DONE]
- [x] Canonical test suite run.
- [x] Compare `ShadowDecision` quality.

---

## Phase 4.2: The Inhibitory Cortex (Safety Gate)
**Goal:** Grant the Mirror **Veto Power** over the Stage 3 Router.

### Step 7: Veto Logic Implementation [DONE]
- [x] Connect `ShadowCortex` to `base_decision` (Mirror must see what it's vetoing).
- [x] Implement `ShadowCortex.veto_check(base_decision)`.
- [x] Define specific `InhibitionRules` for Stage 3 actions.

### Step 8: The Gate [DONE]
- [x] Modifiy `stage3_router.py` to BLOCK action if `veto_check` returns True.
- [x] Implement `Stage4BlockedResponse` (Clean failure mode).

### Step 9: Validation of Control [DONE]
- [x] Test Veto: Force a "bad" decision and verify Stage 4 blocks it.

---

## Phase 4.3: The Switch (Full Autonomy)
**Goal:** Deprecate Stage 3 Router. `ReptileBrain` becomes the Primary Engine.

### Step 10: The Broca Actuation Layer (Real Output) [DONE]
- [x] Implement `Action` definitions using strict Pydantic schemas.
- [x] Connect `BrocaBridge` to `mace.core.action.execute()`.

### Step 11: The Cognitive Loop (Reptile Brain 2.0) [DONE]
- [x] Implement `ReptileBrain.think_step()`: The iteration logic (Plan -> Perceive -> Refine -> Act).
- [x] Implement `ThoughtTrace` logging (The "Stream of Consciousness" log).

### Step 12: The Switchover [DONE]
- [x] Create `stage4_router.py`.
- [x] Route `user_input` -> `ShadowCortex` (now Primary) -> `Broca` -> `Output`.
- [x] Stage 3 becomes a fallback/legacy path.

### Step 13: Validation (The "Autonomy" Test) [DONE]
- [x] **Golden Test:** "Multi-Step Goal."
    *   Prompt: "Research X and then summarize it."
    *   System MUST: Plan (research) -> Act (tool use) -> Perceive (read) -> Plan (summarize) -> Act (reply).
    *   All without the Stage 3 router logic.
