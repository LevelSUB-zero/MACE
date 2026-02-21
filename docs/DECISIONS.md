# MACE Architecture Decision Records (ADR)

> Every architectural decision gets logged here. This is the "why" behind the codebase.
> Format: One paragraph per decision. Reference in `MACE_STATUS.md` and `BACKLOG.md` by ID.

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

*When adding a new decision: use next ID (D-005), include Anti-Drift Check for architectural decisions.*
