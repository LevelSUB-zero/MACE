---
trigger: always_on
---

> **Operational Rules to Maintain the "Artificial Organism" Vision**
> *Mandatory for all planning, architecture, and implementation tasks.*

## 0. The Prime Directive
**The Vision Manifesto (`docs/VISION_MANIFESTO.md`) is the Axiom.**
The Science Discoveries (`docs/sciencediscoveries/`) provide the biological blueprint for implementation.
It is not a suggestion. It is the definition of success. If a feature works perfectly but violates the spirit of the Manifesto (e.g., reduces MACE to a mere tool), it is a **failure**.

## 1. The "Organism" Test
Before implementing any component, apply this heuristic:
*   **Tool Mindset:** "Does this help the user do X?" (WRONG)
*   **Organism Mindset:** "Does this give the system the capability to *understand* and *improve* its ability to do X?" (RIGHT)

**Example:**
*   *Bad:* Add a calculator tool so it can do math. (Chatbot style)
*   *Good:* Add a numerical reasoning cortex so it knows *when* it needs to calculate and can verify its own results. (Organism style)

## 2. Cognition Over Generation
**The System's internal state is more important than its output.**
*   We prioritize the **Observable Cognitive Space** (how it thinks) over the final text response.
*   **Rule:** Never optimize for output quality if it sacrifices the transparency or complexity of the internal thought process. It is better to have a system that "thinks" deeply and outputs simply, than one that hallucinates complexity.

## 3. Governance as DNA
**Governance is not a fence; it is the skeleton.**
*   In standard AI, safety constraints are "guardrails" to keep the car on the road.
*   In MACE, governance (signatures, logs, constitution) is the **DNA**. It defines what the organism *is*.
*   **Rule:** You cannot "turn off" governance to "move fast." That is like removing a skeleton to run faster. You just collapse.

## 4. The Anti-Drift Check (Mandatory Step)
At the start of every new Phase or Major Task, you must explicitly ask:
1.  **"Does this make MACE more autonomous?"** (vs just more responsive)
2.  **"Does this enable future self-regeneration?"** (vs just hard-coded features)
3.  **"Is this distinct from an LLM wrapper?"**
4.  **"Is this aligned with the biological architecture defined in Science Discoveries?"** (vs generic AI architecture)

If the answer is NO to any, **STOP**. Divergence detected.