---
description: How to properly end a coding session and preserve context
---

# End Session Workflow

Follow this workflow at the end of every coding session to preserve context for the next session.

## Steps

1. **Summarize what was done**
   In your final message, provide a clear summary:
   - What tasks were worked on (reference backlog IDs)
   - What was completed vs. what remains
   - Any decisions made
   - Any new issues discovered

2. **Update MACE_STATUS.md**
   - Update the "Current Focus" section with latest status
   - Update task statuses in the table
   - Add any new decisions to the "Recent Decisions" table
   - Update the "Last Updated" date

3. **Update BACKLOG.md**
   - Mark completed tasks as ✅ Done
   - Update in-progress task status
   - Add any newly discovered work items
   - Move items to "Recently Completed" if finished

4. **Log architectural decisions**
   If any architectural decisions were made during the session:
   - Add entry to `docs/DECISIONS.md` with next D-number
   - Include: Date, Context, Decision, Consequences, Anti-Drift Check

5. **Stage commits**
   Suggest or make commits with conventional commit messages:
   ```
   feat(nlu): implement behavior shaping loss masking
   docs(status): update MACE_STATUS for session 2026-02-20
   ```

6. **Flag any drift concerns**
   If you noticed anything during the session that might violate:
   - Vision Manifesto principles
   - Determinism requirements
   - Governance-as-DNA principle
   
   Flag it explicitly so the user can address it.
