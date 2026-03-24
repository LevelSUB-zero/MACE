# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Test Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Set up database (initial setup)
python migrations/migrate_template.py --db mace_stage1.db --sql migrations/0001_create_stage1_tables.sql
python migrations/migrate_template.py --db mace_stage1.db --sql migrations/0002_gap_remediation.sql

# Run full test suite (current stages)
pytest tests/ -v

# Run specific test suites
pytest tests/system/ -v          # Authoritative regression guard (17 tests)
pytest tests/v02_validation/ -v # Validation tests
pytest tests/stage2/ -v          # Stage-2 governance tests
pytest tests/stress/ -v          # Stress tests

# Run single test file
pytest tests/system/test_mace_system.py -v

# Linting
black src/ tests/ --line-length=100
isort src/ tests/ --profile=black
flake8 src/ tests/ --max-line-length=100
```

## Architecture Overview

MACE (Meta Aware Cognitive Engine) is a **deterministic cognitive execution engine**. It is NOT an LLM wrapper — it is the "brain", with LLMs serving as knowledge sources.

### Core Execution Flow

```
User Input → NLU Parser → Router → Agent → Council → Reflective Log → BrainState Save
```

**Key principle**: Every execution is reproducible given the same seed. IDs, timestamps, and randomness are all derived deterministically.

### Module Structure

| Module | Purpose |
|--------|---------|
| `src/mace/runtime/executor.py` | Main execution loop — orchestrates all components |
| `src/mace/router/` | Deterministic agent selection based on NLU intent |
| `src/mace/agents/` | Domain agents (math, profile, knowledge, generic) |
| `src/mace/core/deterministic.py` | Seed management, deterministic IDs/timestamps |
| `src/mace/core/structures.py` | Data structures (percept, agent_output, etc.) |
| `src/mace/brainstate/` | Persistent execution state (goals, working memory) |
| `src/mace/memory/` | Memory hierarchy (WM, CWM, Episodic, Semantic) |
| `src/mace/nlu/` | Natural language understanding (Ollama/Gemma 3) |
| `src/mace/reflective/` | Signed execution logs (HMAC-SHA256) |
| `src/mace/governance/` | Admin tokens, kill-switch, security |
| `src/mace/stage2/` | Epistemic governance (candidates, council labels, amendments) |

### Memory Hierarchy

```
Working Memory (WM) → Contextual WM (CWM) → Episodic Memory → Semantic Memory
                                                              ↑
                                            Candidate Memory → Council Labels
```

- **WM**: 7 items, 10 ticks TTL, FIFO eviction
- **Episodic**: Long-term event storage with deterministic IDs
- **Semantic**: Knowledge graph with PII filtering
- **Candidate Memory**: Transient hypotheses for Council judgment

### Determinism Rules

1. **IDs**: `HMAC-SHA256(seed, namespace:payload:counter)`
2. **Timestamps**: Derived from `HMAC(seed, counter)` offset from base epoch
3. **Router**: Stable sorting with tie-breaking by agent_id
4. **No system randomness**: All PRNG must be seeded

### Test Organization

- `tests/system/` — Authoritative regression suite
- `tests/v02_validation/` — Validation tests
- `tests/stage2/` — Stage-2 governance tests
- `tests/stress/` — Performance stress tests
- `tests/stage1/` — **QUARANTINED** (legacy APIs)
- `tests/debug/`, `tests/stage3-5/` — **EXCLUDED** (future stages)

See `pytest.ini` for exclusions. Future-stage tests are quarantined until their stage is active.

## Key Patterns

### Creating Deterministic IDs

```python
from mace.core import deterministic
deterministic.init_seed("my_seed")
id = deterministic.deterministic_id("percept", text_content)
ts = deterministic.deterministic_timestamp(deterministic.increment_counter("log_time"))
```

### Running an Execution

```python
from mace.runtime import executor
output, log = executor.execute(
    "What is 2+2?",
    intent="math",
    seed="deterministic_seed"
)
```

### Memory Key Normalization

All agents MUST lowercase and sanitize entity values before constructing canonical keys:

```python
subject_key = subject.lower().replace(" ", "_")
```

The `_validate_key` regex only accepts `[a-z0-9_]+`.

### NLU Intent Mapping

The router maps NLU intents to agents. See `src/mace/router/stage1_router.py` for the full `intent_map`. Key intents:

- `math` → `math_agent`
- `profile_store`, `profile_recall` → `profile_agent`
- `fact_teach`, `history_recall` → `knowledge_agent`
- `greeting`, `chitchat`, `unknown` → `generic_agent`

### Database Files

- `mace_stage1.db` — Primary database (BrainState, logs, etc.)
- `mace_memory.db` — Memory storage (WM, Episodic, Semantic)
- `lr01_training.db` — Training artifacts (SNN training)

## Design Principles (Anti-Drift Protocol)

Every feature must pass these checks:

1. **Autonomy**: Does it make the system more self-governing?
2. **Self-regeneration**: Does it enable future learning loops?
3. **Not an LLM wrapper**: MACE is the brain; LLMs are knowledge sources
4. **Biological alignment**: Follows evolutionary cognition (spine → cortex → advisory)

See `docs/DECISIONS.md` for architectural decisions and their rationale.

## Roadmap

| Stage | Name | Status |
|-------|------|--------|
| 1 | Deterministic Execution | ✅ Complete |
| 2 | Memory Governance | ✅ Complete |
| 3 | Advisor (Epistemic Agency) | In Progress |
| 4-6 | [Planned] | Future |
| 7 | Daemon (OS-native persistence) | Planned |
| 8 | Swarm (Autonomous cron agents) | Planned |

## Migrations

Database migrations are SQL files in `migrations/`. Run with:

```bash
python migrations/migrate_template.py --db <database> --sql <migration_file>
```

## Important Files

- `docs/ARCHITECTURE.md` — Detailed system design
- `docs/DECISIONS.md` — Architecture Decision Records
- `docs/specs/SPEC-*.md` — Specification documents
- `docs/phase3/STAGE_3_ELIGIBILITY.md` — Stage 3 readiness checklist