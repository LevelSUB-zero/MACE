---
description: How to start every new AI coding session on MACE
---

# Start Session Workflow

This workflow MUST be followed at the beginning of every new conversation/session.

## Steps

1. **Read the Single Source of Truth**
   Read `MACE_STATUS.md` in the project root. This tells you:
   - What stage the project is at
   - What work is currently active
   - Recent architectural decisions
   - Where things live in the codebase

2. **Read the Backlog**
   Read `BACKLOG.md` in the project root. Identify:
   - What P0 (active) tasks exist
   - What P1 (next up) tasks are ready
   - Any blocked items

3. **Read the Anti-Drift Protocol**
   Read `.agent/rules/zero-divergence-protocol.md`. Internalize:
   - The Organism Test
   - Cognition Over Generation
   - Governance as DNA

4. **Understand the User's Request**
   Now that you have context, interpret the user's request against the current project state.
   Ask clarifying questions if anything is ambiguous.

5. **If implementing a major feature, run the Anti-Drift Check:**
   Ask yourself (and answer in your response):
   - "Does this make MACE more autonomous?" (vs just more responsive)
   - "Does this enable future self-regeneration?" (vs just hard-coded features)
   - "Is this distinct from an LLM wrapper?"
   - "Is this aligned with the biological architecture defined in Science Discoveries?"
   If NO to any → flag divergence to the user.

6. **Read relevant docs**
   Based on the task, read the relevant documentation:
   - For NLU work: `src/mace/nlu/` and NLU-related backlog items
   - For core architecture: `docs/ARCHITECTURE.md`
   - For stage-specific work: `docs/phase{N}/STAGE{N}_TASK.md`
   - For conventions: `docs/CONVENTIONS.md`
