# SPEC: Health Checkup and Stage 3 Eligibility
**Backlog ID:** ARCH-001 (Part 1)
**Date:** 2026-02-27
**Status:** APPROVED
**Owner:** Solo

## 1. Goal
To conduct a comprehensive system health checkup, resolve current test suite errors caused by misaligned, debug, or future-stage test files, and formally evaluate MACE's eligibility to transition into Stage 3 (The Advisor). This ensures the foundational Spino-Cerebellar architecture (Stage 1) and Memory Governance (Stage 2) are absolutely stable and bug-free before introducing new epistemic agency layers.

## 2. Anti-Drift Validation
- ✅ **Autonomy:** Ensuring foundational systems (Memory, NLU, Runtime) are strictly deterministic and solid is required for higher-order autonomous reasoning.
- ✅ **Self-regeneration:** The memory pipeline (transient Candidates) must be verified clean, as it forms the basis of future learning loops.
- ✅ **Not an LLM wrapper:** The health check focuses heavily on validating the non-LLM governance and memory structures.
- ✅ **Biological alignment:** Following evolutionary biology, the lower brain structures (Spine/Reptilian) must be fully mature before the higher cortex (Advisory) develops.

## 3. Design

### 3.1 Architecture
The health check will validate the existing Stage 1 & 2 architecture. It does not introduce new runtime components. Instead, it introduces a "Stage 3 Gate" formalized through test sanitization and a Readiness/Eligibility document.

### 3.2 Components
1. **Test Suite Hygiene (`tests/`)**: 
   - **Current state:** Pytest throws collection errors on `tests/debug/`, `tests/stage4/`, `tests/stage5/`, and a duplication of `test_candidate.py`.
   - **Action:** Quarantine or conditionally skip these future/debug tests by formalizing test discovery.
2. **Eligibility Report (`docs/phase3/STAGE_3_ELIGIBILITY.md`)**:
   - A formal checklist acknowledging that MACE meets all biological and technical requirements to initialize Stage 3.

### 3.3 Data Flow
*N/A - This is an operational, not runtime, design pass.*

### 3.4 Interfaces
- Engineer must configure `.pytest.ini` or use `@pytest.mark.skip` for future stages to guarantee a green `pytest` execution.
- Engineer must verify the health of the system and document it.

## 4. Task Breakdown

| # | Task | Files | Dependencies |
|---|------|-------|-------------|
| 1 | Test Suite Exclusions | `pytest.ini` (create/update) | None |
| 2 | Cleanup Duplicates | `tests/v02_validation/test_candidate.py` OR `tests/stage2/test_candidate.py` | None |
| 3 | Run System Health Check | Terminal / Pytest | Task 1, 2 |
| 4 | Create Eligibility Doc | `docs/phase3/STAGE_3_ELIGIBILITY.md` | Task 3 |

**Details for Task 1:**
- Configure `pytest.ini` to explicitly **exclude** `tests/debug`, `tests/stage4`, and `tests/stage5` from pytest collection. These folders represent scratchpads or future stages that are not currently implemented, and their import failures break the test suite.

**Details for Task 2:**
- Resolve the `import file mismatch` error for `test_candidate.py`. There appear to be duplicate files in `v02_validation/` and `stage2/`. De-duplicate them (likely keeping `v02_validation` per MEM-001 backlog) or ensure they have unique module names. Remove dangling `__pycache__` and `.pyc`.

**Details for Task 3:**
- Run `pytest tests/` and verify `0` collection errors and `0` failed tests (warnings are acceptable).
- Validate that the memory DB is not locked and that all Stage 1 and Stage 2 E2E tests pass.

**Details for Task 4:**
- Create `docs/phase3/STAGE_3_ELIGIBILITY.md` confirming the following checklist:
  - [ ] Stage 1 (Skeleton) is stable and tests pass.
  - [ ] Stage 2 (Memory Governance) is integrated and tested (`MEM-003`, `MEM-002` verified).
  - [ ] NLU parser is fully deterministic and not hallucinating.
  - [ ] Test suite executes sequentially and parallel without IO/db-lock fatal errors.
- If all are green, provide the official sign-off for Stage 3 development.

## 5. Acceptance Criteria
- [ ] Pytest runs with zero errors and zero test failures.
- [ ] `tests/debug/`, `tests/stage4`, and `tests/stage5` are cleanly excluded from collection.
- [ ] Duplicate `test_candidate.py` collection error is resolved.
- [ ] `docs/phase3/STAGE_3_ELIGIBILITY.md` is generated with signed-off criteria verifying readiness.

## 6. Risks & Edge Cases
- SQLite database lock issues on Windows: Ensure that running the full test suite does not trigger file locks. If it does, Engineer might need to adjust test fixtures (e.g. unique DBs per test).

## 7. Decisions Made
- **D-005** (To log in `docs/DECISIONS.md`): Delineate strict boundaries for active testing. Tests for future, unbuilt cognitive stages (4, 5) belong in quarantine/skip configuration until their respective stage is active to prevent blocking CI/CD pipelines.
