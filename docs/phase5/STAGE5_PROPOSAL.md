
# Stage 5: Self-Improvement (Proposal)

Now that MACE has a functioning "Brain" (Stage 4), we move to **Self-Improvement**.

## The Goal
To enable MACE to:
1.  **Sleep:** Process daily logs (`ShadowDecision` traces) into long-term memories.
2.  **Learn:** Update its "Knowledge Graph" (beliefs) based on what worked/failed.
3.  **Code Itself:** Safely modify its own tools (under strict Inhibition rules).

## The Plan
1.  **The Hippocampus (Memory Consolidation):**
    *   Create a `SleepCycle` agent.
    *   It runs when the system is "IDLE".
    *   It compresses `CognitiveFrames` into `EpisodicMemory`.

2.  **Plasticity (Graph Updates):**
    *   Allow the `ReptileBrain` to add new nodes to the `KnowledgeGraph`.
    *   "I learned that 'rm -rf' is dangerous." -> `Graph.add_edge("rm -rf", "dangerous", weight=1.0)`

3.  **The Workshop (Tool Synthesis):**
    *   Allow MACE to write new python scripts in `src/mace/tools/dynamic/`.
    *   **Governance:** The Mirror must VETO any tool that violates DNA (e.g., no network access without permit).

**Ready to start?**
