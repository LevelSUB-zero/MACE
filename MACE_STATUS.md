# 🧠 MACE Mission Control — Single Source of Truth

> **Last Updated:** 2026-02-21
> **Active Stage:** Stage 2 (NLU Parser Pivot)
> **Overall Project Phase:** Stage 1 COMPLETE → Stage 2 (Active) → Stages 3, 4, 5 Pipeline → Stage 6 (The Organism) = VISION

---

## 🚦 Current Focus

### Active Workstream: NLU Parser — Prompt-Engineered Gemma 3 1B
**Goal:** Deterministic NLU using stock Gemma 3 1B with comprehensive prompt engineering + schema validation.
**Approach Pivot (D-004):** Fine-tuning abandoned due to GGUF/CUDA issues; prompt engineering achieves 10/10 accuracy.

| Task | Status | Key Files |
|------|--------|-----------|
| Standardize training data to 8-key JSON schema | ✅ Done | `data/nlu/`, `src/mace/nlu/convert_to_bio.py` |
| Data augmentation (1063 examples) | ✅ Done | `src/mace/nlu/augment_data.py` |
| Fine-tune Llama 3.2 1B (abandoned) | ❌ Abandoned | `notebooks/lightning_behavior_shaping.py` |
| Prompt-engineered NLU with Gemma 3 1B | ✅ Done (10/10) | `src/mace/nlu/ollama_nlu.py` |
| Schema validator + retry loop | ✅ Done | `src/mace/nlu/ollama_nlu.py` |
| Ollama CPU mode (GTX 960M workaround) | ✅ Done | `OLLAMA_NUM_GPU=0` env var |
| Integration with MACE cognitive pipeline | ✅ Done | `src/mace/core/`, `src/mace/runtime/` |

### Blocked / Waiting
- None currently.

---

## 🏗️ Architecture Quick Reference

```
MACE = "Meta Aware Cognitive Engine" — Governed Digital Life, NOT an LLM wrapper.

Evolution Stages:
  Stage 0 (The Stub/Rock)       ✅ DONE
  Stage 1 (The Skeleton/Spine)  ✅ DONE
  Stage 2 (Memory Governance)    🟡 ACTIVE
  Stage 3 (The Advisor/Ghost)    ⚪ PENDING
  Stage 4 (The Mirror/Cortex)    ⚪ PENDING — Shadow Cortex, Meta-Cognition
  Stage 5 (The Architect/Hands)  ⚪ PENDING — Self-Improvement, Tool Synthesis
  Stage 6 (The Organism/Being)   🎯 VISION — True Autonomy

Core Pipeline: Input → Executor → Router → Agent → Council → Reflective Log → BrainState
Key Principle: "Cognition over Generation" — Internal state > output quality
Governance: DNA, not guardrails. Never disable to "move fast."
```

**Authoritative Documents:**
- Vision: `docs/VISION_MANIFESTO.md`
- Architecture: `docs/ARCHITECTURE.md`
- Science Blueprint: `docs/sciencediscoveries/`
- Anti-Drift Protocol: `.agent/rules/zero-divergence-protocol.md`
- Conventions: `docs/CONVENTIONS.md`

---

## 📋 Recent Decisions (last 5)

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| D-004 | 2026-02-20 | Pivot from fine-tuning to prompt-engineered Gemma 3 1B | Fine-tuning had GGUF conversion failures + CUDA crashes on GTX 960M; stock Gemma 3 1B + 19 few-shot examples + schema validator achieves 10/10 accuracy with zero fine-tuning |
| D-003 | 2026-02 | Pivot NLU from BERT to Qwen 1.5B Parser | BERT approach was failing; behavior shaping = deterministic, zero-hallucination NLU |
| D-002 | 2025-12 | v1.0.0 Release (Stage-1 production) | 100% replay fidelity, p95=118ms |
| D-001 | 2025-11 | Adopt "Organism" vision over "Tool" vision | MACE is governed digital life, not an LLM wrapper |

> Full decision history: `docs/DECISIONS.md`

---

## 🗂️ Project Map (Where Things Live)

```
Mace/
├── MACE_STATUS.md          ← YOU ARE HERE (read this first, always)
├── BACKLOG.md              ← What to work on next
├── docs/
│   ├── VISION_MANIFESTO.md ← The Axiom (never changes without governance)
│   ├── ARCHITECTURE.md     ← System design (Stage 1 base)
│   ├── CONVENTIONS.md      ← Naming, style, file organization rules
│   ├── DECISIONS.md        ← Architecture Decision Records (ADR log)
│   ├── specs/              ← Feature specs produced by /plan (Architect)
│   ├── sciencediscoveries/ ← Biological blueprint
│   ├── phase0/ – phase5/   ← Historical stage docs (completed work)
│   └── [stage-specific].md ← Policy/rules docs
├── src/mace/               ← Source code
│   ├── core/               ← Cognitive data structures
│   ├── nlu/                ← Natural Language Understanding (ACTIVE)
│   ├── runtime/            ← Executor
│   ├── router/             ← Agent selection
│   ├── memory/             ← WM, Episodic, Semantic
│   ├── brainstate/         ← Persistent state
│   ├── governance/         ← Admin, kill-switch
│   ├── stage2/ – stage3/   ← Stage-specific modules
│   └── ...
├── tests/                  ← Test suite
├── models/                 ← NLU model files
├── notebooks/              ← Training experiments
├── .agent/
│   ├── rules/
│   │   ├── zero-divergence-protocol.md  ← Anti-drift (always on)
│   │   └── agent-personas.md            ← 3-agent system (always on)
│   └── workflows/
│       ├── plan.md             ← /plan  → Architect persona
│       ├── code.md             ← /code  → Engineer persona
│       ├── review.md           ← /review → Reviewer persona
│       ├── start-session.md    ← /start-session
│       ├── end-session.md      ← /end-session
│       ├── implement-feature.md
│       └── architecture-decision.md
└── tools/                  ← Operational scripts
```

---

## 🤖 Agent Persona System

Three specialized agents, invoked via slash commands. **Always flows:** Architect → Engineer → Reviewer.

| Persona | Command | Role | Produces |
|---------|---------|------|----------|
| 🧭 **Architect** | `/plan` | Strategic design | Specs in `docs/specs/` |
| ⚡ **Engineer** | `/code` | Disciplined implementation | Source code + tests |
| 🔍 **Reviewer** | `/review` | Quality gate | Review verdicts |

**Rules:** Personas don't blend. Architect doesn't code. Engineer doesn't redesign. Reviewer doesn't fix.

---

## ⚠️ Rules for AI Agents

1. **Read this file first** in every new conversation.
2. **Adopt a persona** when invoked via `/plan`, `/code`, or `/review`.
3. **Run the Anti-Drift Check** (`.agent/rules/zero-divergence-protocol.md`) before any major implementation.
4. **Follow workflows** in `.agent/workflows/` for common tasks.
5. **Log decisions** in `docs/DECISIONS.md` for anything architectural.
6. **Update this file** when you complete a task, start new work, or make a decision.
7. **Never contradict** `docs/VISION_MANIFESTO.md`.

---

*This file is the heartbeat of MACE development. Keep it current.*
