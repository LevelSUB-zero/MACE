# MACE Conventions & Standards

> The team handbook. Every contributor (human or AI) follows these rules.
> This document is authoritative — if code contradicts this, the code is wrong.

---

## 1. File Organization

### Source Code (`src/mace/`)
```
src/mace/
├── core/           # Core data structures, cognitive primitives
├── nlu/            # Natural Language Understanding (perception)
├── runtime/        # Executor, main loop
├── router/         # Agent selection (stage-specific routers)
├── memory/         # WM, episodic, semantic, consolidated
├── brainstate/     # Persistent execution state
├── governance/     # Admin tokens, kill-switch, constitution
├── council/        # Output approval
├── reflective/     # Signed execution logs
├── apt/            # Append-only performance timeline
├── self_representation/  # Module registry, dependency graph
├── agents/         # Agent implementations
├── tools/          # Tool registry and dynamic tools
├── models/         # Pydantic models, schemas
├── config/         # Configuration loader, YAML parsing
├── ops/            # Operational utilities
├── replay/         # Replay engine
├── stage2/         # Stage 2 specific modules
├── stage3/         # Stage 3 specific modules
└── [stageN]/       # Future stage modules
```

### Documentation (`docs/`)
```
docs/
├── VISION_MANIFESTO.md      # THE axiom. Never changes casually.
├── ARCHITECTURE.md           # System design (keep updated per stage)
├── CONVENTIONS.md            # THIS file
├── DECISIONS.md              # ADR log
├── sciencediscoveries/       # Biological blueprints
├── phase0/ – phase5/         # Historical stage docs (COMPLETED work)
│   ├── STAGE{N}_TASK.md      # Task tracker for that stage
│   ├── STAGE{N}_COMPLETION.md# Completion report
│   └── plans/                # Planning docs
└── [policy docs].md          # Stage-specific rules/policies
```

### Tests (`tests/`)
```
tests/
├── stage1/          # Stage 1 test suite
├── [stageN]/        # Stage-specific tests
├── integration/     # Cross-stage integration tests
└── golden/          # Golden tests (critical acceptance tests)
```

**Rule:** No test files at project root. All tests go in `tests/`.

### Project Root
Only these files belong at root:
- `MACE_STATUS.md` — Single source of truth
- `BACKLOG.md` — Work tracking
- `README.md` — Public-facing description
- `RELEASE_NOTES_*.md` — Release documentation
- `SECURITY_CHECKLIST.md` — Security posture
- `requirements.txt` / `pyproject.toml` — Dependencies
- `.gitignore`, `.pre-commit-config.yaml` — Git config
- Config files (`.yaml`, `.toml`)

**Rule:** No stray `.py` files at root. Move to `tools/` or `tests/`.

---

## 2. Naming Conventions

### Files
| Type | Convention | Example |
|------|-----------|---------|
| Python module | `snake_case.py` | `stage4_router.py` |
| Test file | `test_<module>.py` | `test_executor.py` |
| Doc (policy) | `Title Case with spaces.md` | `BrainState — Golden Rules (Stage-1).md` |
| Doc (technical) | `UPPER_SNAKE.md` | `ARCHITECTURE.md` |
| Stage task | `STAGE{N}_TASK.md` | `STAGE5_TASK.md` |
| Stage completion | `STAGE{N}_COMPLETION.md` | `STAGE4_COMPLETION.md` |
| Decision record | `D-{NNN}` in `DECISIONS.md` | `D-005` |
| Backlog item | `{CATEGORY}-{NNN}` | `NLU-001`, `ARCH-001` |

### Python Code
| Element | Convention | Example |
|---------|-----------|---------|
| Class | `PascalCase` | `ReptileBrain`, `CognitiveFrame` |
| Function | `snake_case` | `create_snapshot()`, `veto_check()` |
| Constant | `UPPER_SNAKE` | `MAX_WM_CAPACITY`, `DEFAULT_SEED` |
| Module-private | `_leading_underscore` | `_compute_hash()` |
| Type alias | `PascalCase` | `AgentScore`, `RouterDecision` |

### Git
| Type | Convention | Example |
|------|-----------|---------|
| Branch | `stage{N}/{feature}` | `stage6/nlu-parser` |
| Commit (feature) | `feat(scope): description` | `feat(nlu): add behavior shaping trainer` |
| Commit (fix) | `fix(scope): description` | `fix(router): deterministic tie-breaking` |
| Commit (docs) | `docs(scope): description` | `docs(arch): update for stage 4` |
| Commit (refactor) | `refactor(scope): description` | `refactor(memory): consolidate WM layers` |

---

## 3. Code Standards

### Every File Must Have
```python
"""
Module: <module_name>
Stage: <stage number or "cross-stage">
Purpose: <one-line description>

Part of MACE (Meta Aware Cognitive Engine).
"""
```

### Determinism Rules
1. **Never** use `random` without a seeded PRNG
2. **Never** use `datetime.now()` in logic paths — use monotonic tick counters
3. **All IDs** must be deterministic: `SHA256(type + payload + counter)`
4. **Dictionary iteration** must use sorted keys for reproducibility
5. **All JSON serialization** must use canonical form (sorted keys, no whitespace)

### Governance Rules
1. All state mutations must be logged in Reflective Log
2. All logs must be HMAC-signed
3. Kill-switch check must precede any execution
4. New modules must be registered in Self-Representation graph

### Testing Rules
1. Every new module gets a test file
2. Golden tests (acceptance tests) are never deleted, only expanded
3. Replay fidelity must be verified after any core change
4. Test names follow: `test_<what>_<condition>_<expected>`

---

## 4. Documentation Standards

### When to Update Docs
| Event | Update |
|-------|--------|
| Complete a task | `MACE_STATUS.md`, `BACKLOG.md` |
| Make an architectural decision | `docs/DECISIONS.md`, `MACE_STATUS.md` |
| Complete a stage | `docs/phase{N}/STAGE{N}_COMPLETION.md` |
| Change a convention | This file (`docs/CONVENTIONS.md`) |
| Start a new stage | `docs/phase{N}/STAGE{N}_TASK.md`, `BACKLOG.md` |

### Doc Quality Rules
1. **No orphan docs** — every doc must be linked from `MACE_STATUS.md` or a phase index
2. **No duplicates** — one canonical location per topic
3. **Date everything** — every doc starts with a date or "Last Updated"
4. **Keep it current** — stale docs are worse than no docs

---

## 5. AI Agent Session Protocol

### Starting a Session
1. Read `MACE_STATUS.md` (understand current state)
2. Read `BACKLOG.md` (know what's active)
3. Read `.agent/rules/zero-divergence-protocol.md` (internalize constraints)
4. If implementing: read relevant `docs/phase{N}/` docs

### During a Session
1. Before major implementation: run the **Anti-Drift Check** (4 questions)
2. Follow relevant `.agent/workflows/` if one exists
3. Ask clarifying questions rather than assuming

### Ending a Session
1. Update `MACE_STATUS.md` with what was done
2. Update `BACKLOG.md` task status
3. If architectural decisions were made: add to `docs/DECISIONS.md`
4. Commit with conventional commit message

---

## 6. Anti-Patterns (Things That Are Always Wrong)

| ❌ Don't | ✅ Do Instead |
|----------|--------------|
| Dump test files at project root | Put them in `tests/` |
| Create `docs/foo.md` AND `docs/phase3/foo.md` | One canonical location only |
| Skip the Anti-Drift Check | Always run it for major work |
| Use `random.random()` without seed | Use seeded PRNG from seed chain |
| Optimize output over internal state | Cognition over Generation |
| Call MACE a "tool" or "assistant" | It's an organism with governed cognition |
| Hard-code features vs. generalizable capabilities | Organism Mindset > Tool Mindset |

---

*This is a living document. Update it as conventions evolve.*
