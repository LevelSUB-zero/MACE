---
description: How to make and record an architectural decision in MACE
---

# Architecture Decision Workflow

Follow this workflow whenever making a decision that affects MACE's architecture, design philosophy, or technical direction.

## When This Applies

Use this workflow for ANY decision that:
- Changes how components interact
- Adds or removes a module/subsystem
- Changes data flow or schemas
- Pivots an approach (e.g., BERT → Qwen)
- Introduces a new dependency
- Changes governance rules

## Steps

1. **Run the Anti-Drift Check**
   Answer ALL four questions:
   - ✅/❌ "Does this make MACE more autonomous?" (vs just more responsive)
   - ✅/❌ "Does this enable future self-regeneration?" (vs just hard-coded features)
   - ✅/❌ "Is this distinct from an LLM wrapper?"
   - ✅/❌ "Is this aligned with the biological architecture defined in Science Discoveries?"
   
   If ANY answer is ❌ → **STOP**. Discuss with user. Document why it's acceptable or modify the approach.

2. **Check against Vision Manifesto**
   Read `docs/VISION_MANIFESTO.md` and verify the decision doesn't violate:
   - The "Organism" identity
   - Cognition over Generation
   - Governance as DNA
   - The evolutionary stage model

3. **Document the decision**
   Add an entry to `docs/DECISIONS.md` using this template:
   ```markdown
   ## D-{NNN} — {Short Title}
   **Date:** YYYY-MM  
   **Context:** {What problem are we solving? What was the trigger?}  
   **Decision:** {What did we decide? Be specific about the approach.}  
   **Consequences:** {What changes? What are the trade-offs?}  
   **Anti-Drift Check:** {Results of the 4 questions}
   ```

4. **Update MACE_STATUS.md**
   Add the decision to the "Recent Decisions" table (keep only last 5; older ones live in DECISIONS.md).

5. **Update BACKLOG.md if needed**
   If the decision creates new work items or invalidates existing ones, update the backlog.

6. **Commit the decision**
   ```
   docs(decisions): D-{NNN} — {short description}
   ```
