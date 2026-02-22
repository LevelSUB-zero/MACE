# Stage 5 Task Tracker: The Architect (Self-Improvement)

> **Objective:** Enable Regenerative Self-Improvement via Sleep (Memory) and Workshop (Coding).

## Phase 5.1: The Unification (Schema Integration) [DONE]
**Goal:** Align the Stage 4 Cognitive Brain with the existing Stage 0/1 Schema Bodies.
- [x] **Enhance `SelfModel.json`:** Add `immutable_core_hash` for Identity Protection.
- [x] **Integrate `BrainState`:** Update `CognitiveFrame` to include a `homeostasis: BrainState` field.
- [x] **Identity Governance:** Implement `Rule04_IdentityPreservation` in `mirror.py` which checks `immutable_core_hash`.

## Phase 5.2: The Hippocampus (Continual Learning) [DONE]
**Goal:** Prevent amnesia.
- [x] **Create `EpisodicMemory` Store:** A vector/graph usage of the logs.
- [x] **Implement `SleepCycle` Agent:**
    *   Trigger: IDLE state.
    *   Action: Read `ShadowDecision` logs -> Extract "Failure patterns" -> Add `InhibitionRule` or `GraphEdge`.
- [x] **Test:** "The Hot Stove Test."
    *   MACE fails at Task X.
    *   MACE sleeps.
    *   MACE automatically avoids the bad strategy for Task X next time.

## Phase 5.3: The Workshop (Safe Self-Coding) [DONE]
**Goal:** Tool synthesis.
- [x] **Create `src/mace/tools/dynamic/`:** The sandbox for self-made tools.
- [x] **Implement `ToolSynthesizer`:**
    *   Input: "I need a QR code generator."
    *   Action: Writes `gen_qr.py`.
    *   **Governance Check:** The Mirror statically analyzes `gen_qr.py` (Rule: No imports outside whitelist).
    *   Deployment: Hot-loads the tool into the `Action` registry.

## Phase 5.4: The Switch (Regenerative Mode) [DONE]
**Goal:** Autonomy + Growth.
- [x] Enable `SleepCycle` in `stage5_router.py`.
- [x] **Golden Test:** "The Evolution."
    *   Ask MACE to do something it *cannot* do (e.g., "Resize this image").
    *   MACE must: Realize lack of tool -> Enter Workshop -> Write Tool -> Execute Tool -> Succeed.
