# MACE Architecture Decision Records (ADR)

> Every architectural decision gets logged here. This is the "why" behind the codebase.
> Format: One paragraph per decision. Reference in `MACE_STATUS.md` and `BACKLOG.md` by ID.

---

## D-008 — Stage 7 & 8 Roadmap Expansion (Autonomous Daemons)
**Date:** 2026-03-16  
**Context:** Research into Open Claw's daemon architecture and recent breakthroughs in biological connectome simulation revealed that true "always-on" autonomy requires separating execution from an interactive frontend. Relying on an open IDE or terminal is insufficient for the "Robo-Police" Organism vision.  
**Decision:** Expand the official MACE evolution roadmap to include Stage 7 (The Daemon: OS-native background persistence via launchd/systemd/schtasks) and Stage 8 (The Swarm: Autonomous cron-based isolated agent turns). Logged ARCH-003 to track the architectural spike.  
**Consequences:** Sets a clear, definitive end-game for MACE's persistent operation. Avoids premature optimization by formally slotting these features *after* Stage 6, allowing current cognitive stages to be built out without distraction.  
**Anti-Drift Check:** ✅ Autonomy — system will eventually run continuously in the background. ✅ Deterministic — relies on scheduled OS runs and highly structured state loops.

---

## D-007 — Test Suite Overhaul + Replay Entity Passthrough
**Date:** 2026-02-27  
**Context:** The v02_validation and stress test suites had 12+ stale assertions from the pre-NLU agent refactor (e.g. `"Stored X = Y"` → `"Got it! Your X is Y."`). Additionally, the router used `datetime.utcnow()` which produced non-deterministic timestamps, breaking replay comparisons. The replay module also didn't pass `entities` from the logged percept back into the executor, causing agents to produce different output during replay.  
**Decision:** (1) Replace `datetime.utcnow()` with deterministic timestamp in router. (2) Add `entities` parameter to `executor.execute()` and have `replay.py` pass logged entities through. (3) Use `INSERT OR REPLACE` in reflective_writer for idempotent log writes. (4) Create canonical `tests/system/test_mace_system.py` (17 tests) as the authoritative regression guard.  
**Consequences:** All 187 tests pass (0 failures). Replay is now fully deterministic with entity passthrough. The new system test suite becomes the Stage 3 gateway guard.  
**Anti-Drift Check:** ✅ Autonomy — replay self-verification is now complete. ✅ Self-regeneration — system can now verify itself. ✅ Deterministic — router timestamps derived from seed.

---

## D-006 — Test Suite Quarantine for Future Stages
**Date:** 2026-02-27  
**Context:** The test suite threw collection errors on `tests/debug/`, `tests/stage4/`, and `tests/stage5/` due to missing modules that have not been implemented yet, which blocked CI/CD and the Stage 3 readiness check.  
**Decision:** Delineate strict boundaries for active testing. Tests for future, unbuilt cognitive stages (4, 5) belong in quarantine/skip configuration (`pytest.ini` exclusions) until their respective stage is active.  
**Consequences:** Prevents unbuilt stages from breaking the test suite of current stable stages. Provides a clean baseline for Stage 3 eligibility.  
**Anti-Drift Check:** ✅ Autonomy — system stability is properly bounded to implemented behavior.

---

## D-005 — Agent Key Normalization Requirement
**Date:** 2026-02-22  
**Context:** During MEM-002 E2E testing, `profile_agent` was constructing canonical keys using raw NLU entity values (e.g. `user/contacts/John/role`). The `_validate_key` regex (`[a-z0-9_]+`) silently rejected these, causing `put_sem` to return `INVALID_KEY_FORMAT` with no visible error.  
**Decision:** All agents MUST lowercase and sanitize entity values before constructing canonical keys. Added `subject_key = subject.lower().replace(" ", "_")` normalization in `profile_agent.py`.  
**Consequences:** Prevents silent data loss from case mismatches. Future agents must follow the same normalization pattern.  
**Anti-Drift Check:** ✅ Governance-as-DNA — key validation is structural, not optional. ✅ Deterministic — same input always produces same key.

---

## D-004 — NLU Pivot 2: Gemma 3 1B Prompt-Engineered Parser
**Date:** 2026-02-20  
**Context:** Fine-tuning approach from D-003 had GGUF conversion failures and CUDA crashes on GTX 960M hardware.  
**Decision:** Pivot to stock Gemma 3 1B using 19 few-shot examples + strict JSON schema validator.  
**Consequences:** Achieves 10/10 zero-hallucination accuracy on tests with zero fine-tuning required. Simplifies architecture and allows CPU inference.  
**Anti-Drift Check:** ✅ Aligns with determinism. ✅ Retains local-only privacy constraint.

---

## D-003 — NLU Pivot: BERT → Qwen 1.5B Behavior-Shaped Parser
**Date:** 2026-02  
**Context:** The BERT-based NLU (intent classification + NER) was producing unreliable results. Hallucinations in entity extraction were unacceptable for a system that requires deterministic cognition.  
**Decision:** Pivot to a generative approach using Qwen 2.5 1.5B fine-tuned with "Behavior Shaping" — training the model to produce a strict 8-key JSON schema via input→output pattern matching (no instructions, loss masking on input tokens). At inference, constrained decoding via JSON grammar with temperature=0 ensures zero hallucination.  
**Consequences:** Requires re-training pipeline, new model hosting (Ollama), and updated inference code. But produces deterministic, structured NLU output that aligns with MACE's core principle of determinism.  
**Anti-Drift Check:** ✅ Deterministic NLU = organism can "hear" reliably. ✅ Enables self-regeneration (can retrain on new data). ✅ Not an LLM wrapper (it's a purpose-trained cortex). ✅ Aligns with biological cognition (perception pathway).

---

## D-002 — v1.0.0 Production Release (Stage 1)
**Date:** 2025-12-03  
**Context:** Stage 1 achieved 100% replay fidelity, comprehensive security (HMAC signatures, kill-switch), and p95=118ms latency.  
**Decision:** Tag v1.0.0 release. Mark Stage 1 as production-ready baseline for all future development.  
**Consequences:** Establishes the deterministic execution contract that all future stages must honor.

---

## D-001 — Adopt "Organism" Vision, Reject "Tool" Paradigm
**Date:** 2025-11  
**Context:** MACE could have been built as a sophisticated LLM orchestration tool (like LangChain, AutoGen, etc.). That path is well-trodden and easier.  
**Decision:** MACE will be an "Artificial Organism" — governed digital life that thinks, not just generates. LLMs are knowledge sources, not the brain. MACE is the brain.  
**Consequences:** Every feature must pass the "Organism Test" (does it let the system *understand*, not just *do*). Governance is DNA, not guardrails. This makes development harder but creates something fundamentally different from existing AI tools.  
**Canonical Reference:** `docs/VISION_MANIFESTO.md`

---

*When adding a new decision: use next ID (D-008), include Anti-Drift Check for architectural decisions.*
