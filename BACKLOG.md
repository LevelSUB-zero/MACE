# MACE Backlog

> **Priority Key:** P0 = Critical/Now, P1 = Next Up, P2 = Soon, P3 = Someday
> **Status Key:** 🔴 Blocked, 🟡 In Progress, 🟢 Ready, ✅ Done, ❄️ Ice Box

---

## 🔥 P0 — Current Sprint (Active Work)

### NLU-001: Deterministic NLU Parser
- **Status:** ✅ Done (via prompt engineering pivot)
- **Owner:** Solo
- **Goal:** Deterministic NLU parser that outputs structured JSON
- **Approach:** Stock Gemma 3 1B + 19 few-shot examples + schema validator (fine-tuning abandoned)
- **Acceptance Criteria:**
  - [x] Training data standardized to 8-key JSON schema (1063 examples)
  - [x] Constrained decoding (Ollama `format:json`, temp=0) prevents hallucination
  - [x] Zero-hallucination on test set (10/10 passed)
  - [x] Schema validator + 3-retry loop + keyword fallback
- **Key Files:** `src/mace/nlu/ollama_nlu.py`, `models/Modelfile`
- **Decision Ref:** D-003, D-004

### NLU-002: Parser Integration with MACE Pipeline
- **Status:** ✅ Done
- **Owner:** Solo
- **Goal:** Wire the NLU parser into the MACE cognitive execution pipeline
- **Acceptance Criteria:**
  - [x] `ollama_nlu.py` updated with Gemma 3 1B + prompt engineering
  - [x] Router can receive structured NLU output
  - [x] End-to-end test: user input → NLU → Router → Agent → Output
  - [x] SQLite DB locking fixed during Pytest execution on Windows
- **Key Files:** `src/mace/runtime/executor.py`, `src/mace/router/stage1_router.py`, `tests/v02_validation/test_executor_v2.py`

### MEM-001: Stage-2 Candidate Generation & Testing Pipeline
- **Status:** ✅ Done
- **Owner:** Solo
- **Goal:** Implement transient Candidate object generation from raw Episodic traces, answering "Is this recurring", and write holistic end-to-end memory pipeline tests to guarantee data flow integrity.
- **Acceptance Criteria:**
  - [x] Implement deterministic Candidate clustering matching the 6 frozen features
  - [x] Candidates contain exact feature keys without LLM generation
  - [x] End-to-end memory pipeline test tests API calls (saving, retrieving)
- **Key Files:** `src/mace/memory/candidate.py`, `tests/v02_validation/test_memory_pipeline.py`
- **Spec Ref:** `docs/specs/SPEC-MEM-001.md`

### MEM-002: Holistic Memory Saving & Retrieving Validation (E2E)
- **Status:** ✅ Done
- **Owner:** Solo
- **Goal:** Validate reliability of MACE's memory pipeline with 14 E2E tests (6 tiers) using real Gemma 3 1B NLU — no mocking.
- **Acceptance Criteria:**
  - [x] MACE correctly maps `profile_store` percept -> commits to semantic DB (name, color, location)
  - [x] MACE correctly accesses previously committed value with `profile_recall` in a *separate* executor call
  - [x] MACE correctly handles `contact_store`/`contact_recall` for third-party entities
  - [x] MACE correctly handles `fact_teach` and `history_search` lifecycle via knowledge agent
  - [x] Episodic memory auto-records interactions and supports keyword search
  - [x] Knowledge Graph accumulates entity attributes across interactions
  - [x] Rapid sequential execution of saves and retrievals does not raise SQLite `Database is locked`
- **Key Files:** `tests/v02_validation/test_memory_retrieval.py`, `src/mace/agents/profile_agent.py`, `src/mace/nlu/ollama_nlu.py`
- **Spec Ref:** `docs/specs/SPEC-MEM-002.md`
- **Bugs Fixed:** Profile agent canonical key case sensitivity, NLU few-shot coverage gaps

---

## 🟠 P1 — Next Up

### ARCH-001: Stage 3, 4, 5 Planning & Execution
- **Status:** ⚪ To Do
- **Goal:** Execute the pipeline for Stages 3, 4, and 5 before moving to Stage 6 (The Organism).
- **Tasks:**
  - [ ] Stage 3: Advisory System & Authority Boundaries
  - [ ] Stage 4: Shadow Cortex & Evolution
  - [ ] Stage 5: Tool Synthesis & Final Pre-Stage-6 Golden Tests
  - [ ] Anti-Drift Check against Vision Manifesto at each stage
- **Depends On:** NLU-001 (parser must work before organism can "hear")

### INFRA-001: README Modernization
- **Status:** 🟢 Ready
- **Goal:** Update README.md to reflect current state (Stages 0-5 done, NLU pivot)
- **Tasks:**
  - [ ] Update version, status, architecture diagram
  - [ ] Add NLU section
  - [ ] Link to MACE_STATUS.md

---

## 🔵 P2 — Soon

### DEBT-001: Documentation Cleanup
- **Status:** 🟢 Ready
- **Goal:** Eliminate duplicate docs, establish single-source-of-truth per topic
- **Tasks:**
  - [ ] Audit: which docs in `docs/` root are duplicated in `docs/phase*/`
  - [ ] Move canonical versions to phase folders, delete root duplicates
  - [ ] Add `_INDEX.md` to each phase folder listing its contents
  - [ ] Remove stale root-level files (`STAGE4_ANSWER.md`, `STAGE_0_READINESS.md`, etc.)

### DEBT-002: Test Consolidation
- **Status:** ✅ Done
- **Goal:** Move stray test files from root into `tests/`
- **Tasks:**
  - [x] Move `test_final.py`, `test_memory_debug.py`, `test_nlu_parser.py`, `test_router_debug.py` into `tests/debug`
  - [x] Verified and moved out of root.

### QUALITY-001: Pre-Commit Hooks Enhancement
- **Status:** 🟢 Ready
- **Goal:** Add anti-drift checks to pre-commit
- **Tasks:**
  - [ ] Add lint rule: no `import random` without seed (determinism)
  - [ ] Add check: all new files must have docstring with stage reference
  - [ ] Verify `.pre-commit-config.yaml` is current

---

## ❄️ P3 — Ice Box (Someday)

### PERF-001: Async I/O for Database
- Migrate SQLite to async for non-blocking BrainState operations

### MONITOR-001: Prometheus/Grafana Integration
- Export metrics for production monitoring

### INFRA-002: Docker Containerization
- Containerize MACE for reproducible deployment

---

## ✅ Recently Completed

| ID | Description | Completed |
|----|-------------|-----------|
| MEM-003 | Memory Persistence & Cross-Layer Search | 2026-02-26 |
| MEM-002 | Holistic Memory Saving & Retrieving | 2026-02-26 |
| NLU-001 | NLU Parser — Gemma 3 1B prompt engineering (10/10) | 2026-02-20 |
| NLU-AUGMENT | Data augmentation pipeline (1063 examples) | 2026-02 |
| NLU-DATA | Training data standardization | 2026-02 |
| STAGE5 | Stage 5 — The Architect (Self-Improvement) | 2025-12 |
| STAGE4 | Stage 4 — The Mirror (Meta-Cognition) | 2025-12 |
| STAGE3 | Stage 3 — The Advisor (Epistemic Agency) | 2025-11 |
| STAGE1-2 | Stages 1-2 — The Skeleton | 2025-11 |
| STAGE0 | Stage 0 — The Stub | 2025-11 |

---

*Update this file when: starting new work, completing tasks, or reprioritizing.*
