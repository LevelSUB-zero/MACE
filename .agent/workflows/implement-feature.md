---
description: How to implement a new feature or module in MACE
---

# Implement Feature Workflow

Follow this workflow when implementing any new feature, module, or significant change.

## Pre-Implementation

1. **Identify the backlog item**
   Every feature should correspond to a `BACKLOG.md` entry.
   If one doesn't exist, create it first with proper ID and acceptance criteria.

2. **Run the Anti-Drift Check**
   Answer these 4 questions explicitly:
   - "Does this make MACE more autonomous?"
   - "Does this enable future self-regeneration?"
   - "Is this distinct from an LLM wrapper?"
   - "Is this aligned with the biological architecture?"
   If NO to any → STOP and discuss with user.

3. **Check conventions**
   Read `docs/CONVENTIONS.md` for:
   - File placement (which directory?)
   - Naming conventions
   - Required docstring format
   - Determinism rules

## Implementation

4. **Write the code**
   - Follow the module docstring template
   - Use deterministic patterns (seeded PRNG, monotonic counters)
   - Register new modules in Self-Representation if applicable

5. **Write tests**
   - Place in `tests/` (appropriate subdirectory)
   - Follow naming: `test_<what>_<condition>_<expected>`
   - Include golden test if this is a critical capability

6. **Verify**
   - Run the relevant test suite
   - Check for import errors
   - Verify replay fidelity if touching core pipeline

## Post-Implementation

7. **Update tracking docs**
   - Update `BACKLOG.md` — mark task as done or update status
   - Update `MACE_STATUS.md` — reflect current state
   - If architectural decision: add to `docs/DECISIONS.md`

8. **Commit**
   Use conventional commit format:
   ```
   feat(scope): description
   fix(scope): description  
   docs(scope): description
   refactor(scope): description
   ```
