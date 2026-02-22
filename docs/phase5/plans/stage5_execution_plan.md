# Stage 5 Execution Plan: "The Architect"

> **Objective:** To enable **Regenerative Self-Improvement** via dynamic memory consolidation (The Sleep Cycle) and governed self-coding (The Workshop).

## Theoretical Basis
Based on `continual_learning_architecture.md` (CLS Theory) and `VISION_MANIFESTO.md` (Stage 5).
The Organism must:
1.  **Sleep:** To consolidate episodes into semantic rules.
2.  **Grow:** To densify its Knowledge Graph.
3.  **Build:** To create new tools for itself.

---

## Phase 5.1: The Unification (Schema Integration)
**Goal:** Align the Stage 4 Cognitive Brain with the existing Stage 0/1 Schema Bodies.
*   [ ] **Enhance `SelfModel.json`:** Add `immutable_core_hash` for Identity Protection.
*   [ ] **Integrate `BrainState`:** Update `CognitiveFrame` to include a `homeostasis: BrainState` field.
*   [ ] **Identity Governance:** Implement `Rule04_IdentityPreservation` in `mirror.py` which checks `immutable_core_hash`.

## Phase 5.2: The Hippocampus (Continual Learning)
**Goal:** Prevent amnesia.
*   [ ] **Create `EpisodicMemory` Store:** A vector/graph usage of the logs.
*   [ ] **Implement `SleepCycle` Agent:**
    *   Trigger: IDLE state.
    *   Action: Read `ShadowDecision` logs -> Extract "Failure patterns" -> Add `InhibitionRule` or `GraphEdge`.
*   [ ] **Test:** "The Hot Stove Test."
    *   MACE fails at Task X.
    *   MACE sleeps.
    *   MACE automatically avoids the bad strategy for Task X next time.

## Phase 5.3: The Workshop (Safe Self-Coding)
**Goal:** Tool synthesis.
*   [ ] **Create `src/mace/tools/dynamic/`:** The sandbox for self-made tools.
*   [ ] **Implement `ToolSynthesizer`:**
    *   Input: "I need a QR code generator."
    *   Action: Writes `gen_qr.py`.
    *   **Governance Check:** The Mirror statically analyzes `gen_qr.py` (Rule: No imports outside whitelist).
    *   Deployment: Hot-loads the tool into the `Action` registry.

## Phase 5.4: The Switch (Regenerative Mode)
**Goal:** Autonomy + Growth.
*   [ ] Enable `SleepCycle` in `stage5_router.py`.
*   [ ] **Golden Test:** "The Evolution."
    *   Ask MACE to do something it *cannot* do (e.g., "Resize this image").
    *   MACE must: Realize lack of tool -> Enter Workshop -> Write Tool -> Execute Tool -> Succeed.

---

## Technical Stack
*   **Analysis:** AST (Abstract Syntax Tree) for code safety checks.
*   **Memory:** Vector Database (FAISS) + JSON Graph.
*   **Execution:** `exec()` (Strictly sandboxed).
