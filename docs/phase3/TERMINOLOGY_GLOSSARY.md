# Stage-3 Terminology Lock (Glossary)

> P1 Item 14: Words carry weight. Define ruthlessly or rename.

---

## Core Terms

| Term | Definition | NOT |
|------|------------|-----|
| **Advisory** | Structured suggestion artifact | Not advice-giving entity |
| **Council** | Governance review module | Not a group of agents |
| **Observation** | Immutable log entry | Not consciousness |
| **Learning** | Weight update via gradient | Not happening in Stage-3 |
| **Divergence** | Mismatch between suggestion and outcome | Not error signal |

---

## Architectural Terms

| Term | Definition |
|------|------------|
| **ReflectiveLog** | Append-only durable storage for advisory artifacts |
| **Guard** | Runtime enforcement of containment invariants |
| **Kill-Switch** | One-way halt mechanism, externally monitored |
| **Shadow Mode** | MEM-SNN observes without influence |
| **Advisory Mode** | MEM-SNN generates suggestions, still no influence |

---

## Forbidden Anthropomorphisms

| Do NOT Say | Say Instead |
|------------|-------------|
| "The model thinks" | "The model outputs" |
| "The system decided" | "The router selected" |
| "Learning from mistakes" | "Divergence logged" |
| "Improving over time" | "Historical patterns recorded" |
| "The council agreed" | "Council review completed" |

---

## Semantic Precision Rules

1. **Confidence** is a textual label, not a probability
2. **Suggestion** is a structured payload, not a recommendation
3. **Observation** is descriptive, not prescriptive
4. **Divergence** is informational, not actionable

---

## Enforcement

Code review must flag:
- Anthropomorphic comments
- Misleading variable names
- Documentation that implies agency
