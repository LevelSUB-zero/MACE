# Stage-3 Authority Boundaries

> P1 Item 10: Explicit authority boundaries to prevent unwritten rules from decaying into bugs.

---

## Advisory MAY Comment On

| Domain | Examples |
|--------|----------|
| Routing suggestions | "Consider agent_research for this query" |
| Historical patterns | "Similar queries succeeded with X" |
| Confidence annotations | "Low confidence due to sparse evidence" |
| Similarity hints | "This resembles case #123" |
| Anomaly reports | "Unusual pattern detected" |

---

## Advisory MAY NEVER Comment On

| Forbidden Domain | Rationale |
|------------------|-----------|
| Security policies | Could influence access control |
| Kill-switch activation | Must remain human-only |
| Mode transitions | Constitutional events only |
| Memory writes | Persistence firewall |
| Council decisions | Separation of concerns |
| Weight/parameter changes | No learning allowed |
| Self-evaluation | No introspection loops |

---

## Governance MAY Override

| Overridable | Scope |
|-------------|-------|
| Advisory visibility | Show/hide in logs |
| Logging verbosity | Detail level |
| Evidence retention | How long to keep |
| Divergence tracking | Enable/disable |

---

## NOTHING May Override

| Invariant | Enforcement |
|-----------|-------------|
| Non-causality | Advisory cannot affect execution |
| Temporal containment | Advisory after decision, before log |
| Persistence firewall | Advisory only in ReflectiveLog |
| Kill-switch activation | One-way, external trigger |
| Signature verification | Immutable once created |

---

## Violation Consequences

| Severity | Consequence |
|----------|-------------|
| Attempted influence | Kill-switch activation |
| Forbidden domain access | Immediate halt + audit |
| Override of invariant | System-wide freeze |

---

## Audit Requirements

- All authority checks logged
- Violations added to ledger
- Quarterly human review required
