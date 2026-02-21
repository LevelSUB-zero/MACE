# SPEC: Holistic Memory Saving & Retrieving Validation (E2E)
**Backlog ID:** MEM-002
**Date:** 2026-02-21
**Status:** DRAFT → APPROVED

## 1. Goal
Validate the reliability of MACE's Stage-1 and Stage-2 memory boundaries by building robust, end-to-end (E2E) tests. These tests must guarantee that the `ProfileAgent` and `KnowledgeAgent` can autonomously write values to Semantic Memory (`semantic.put_sem`) and subsequently read those exact values (`semantic.get_sem`) across multiple deterministic execution cycles. Furthermore, we need to ensure the system does not "crumble" from SQLite database locks when future stages (Stage 3, 4, 5) execute rapidly.

## 2. Anti-Drift Validation
- ✅ **Autonomy**: Reliable memory fetch ensures the organism can independently retrieve context without prompting.
- ✅ **Self-regeneration**: Accurate saving and retrieving of long-term state is the foundation upon which self-improvement mechanisms (Stage 5 Tools) rely.
- ✅ **Not an LLM wrapper**: Validating `mace.memory.semantic` key-value graph paths ensures the system relies on structured schema logic, not stochastic context-window injection.
- ✅ **Biological alignment**: Checks long-term memory formation and recall mimicking hippocampal-neocortical retrieval.

## 3. Design

### 3.1 Architecture
This effort spans the `Executor` -> `Router` -> `Agent` -> `Semantic Memory` stack. The tests will simulate multiple independent user interactions spanning time to verify persistence.

### 3.2 Components
- `tests/v02_validation/test_memory_retrieval.py`: New integration test file.
- `src/mace/memory/semantic.py` (Investigation target for potential bugs).
- `src/mace/agents/profile_agent.py` & `src/mace/agents/knowledge_agent.py` (Validation targets).
- Test Database teardown fixtures (Ensuring test-isolation).

### 3.3 Data Flow involved in test
1. Test injects "store my name as Alice" (Intent: `profile_store`).
2. `profile_agent` executes `semantic.put_sem("user/profile/user_123/name", "Alice")`.
3. Test inspects database existence directly.
4. Test injects "what is my name?" (Intent: `profile_recall`).
5. `profile_agent` executes `semantic.get_sem("user/profile/user_123/name")`.
6. Assert correct textual retrieval in agent response.

### 3.4 Interfaces
```python
# tests/v02_validation/test_memory_retrieval.py

import unittest
from mace.runtime import executor
from mace.memory import semantic

class TestMemoryRetrieval(unittest.TestCase):
    def test_profile_memory_lifecycle(self): ...
    def test_knowledge_memory_lifecycle(self): ...
    def test_concurrent_or_rapid_sqlite_writes(self): ...
```

## 4. Task Breakdown

| # | Task | Files | Dependencies |
|---|------|-------|-------------|
| 1 | Create robust isolated DB cleanup mechanism for sequential tests | `tests/v02_validation/test_memory_retrieval.py` | None |
| 2 | Implement `test_profile_memory_lifecycle` | `tests/v02_validation/test_memory_retrieval.py` | Task 1 |
| 3 | Implement `test_knowledge_memory_lifecycle` | `tests/v02_validation/test_memory_retrieval.py` | Task 1 |
| 4 | Fix any SQLite configuration issues if writing multiple rapid items fails | `src/mace/memory/storage_backend.py` | Task 2, 3 |

## 5. Acceptance Criteria
- [ ] MACE correctly maps `profile_store` percept -> commits to semantic DB.
- [ ] MACE correctly accesses previously committed value with `profile_recall` percept in a *separate* executor call.
- [ ] MACE correctly handles `fact_teach` and `history_search` lifecycle via knowledge agent.
- [ ] Rapid sequential execution of saves and retrievals does not raise SQLite `Database is locked` or `I/O operation on closed file` exceptions.

## 6. Risks & Edge Cases
- **Test Database Contamination**: If the database file is not properly closed between tests, saving Alice's name in one test might bleed into another, causing unexpected equality assertion failures.
- **NLU Hallucinations in Tests**: Testing via raw text requires the prompt-engineered NLU to accurately extract `entities={"attribute": "name", "value": "Alice"}`.

## 7. Decisions Made
- All future memory tests MUST utilize isolated deterministic job seeds to ensure that `Episodic Memory` and `Semantic Memory` logs do not violate SQLite `UNIQUE` constraints across the testing suite.
