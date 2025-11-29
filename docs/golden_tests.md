# Golden Tests (Stage-0)

## G1 — Favorite Color Recall
**Objective**: Verify SEM storage and retrieval via Profile Agent.
1. **Write**: `user/profile/user_123/favorite_color` = "blue"
2. **Query**: "What is my favorite color?"
3. **Expected**:
   - Router: `profile_agent` (Reason: `matched_R2_profile`)
   - SEM Read: `user/profile/user_123/favorite_color` -> "blue"
   - Output: "blue" (or natural language equivalent)

## G2 — Last Write Wins
**Objective**: Verify deterministic overwrite.
1. **Write**: `user/profile/user_123/favorite_color` = "green" (t1)
2. **Write**: `user/profile/user_123/favorite_color` = "red" (t2)
3. **Query**: "What is my favorite color?"
4. **Expected**:
   - Output: "red"
   - SEM Read: Returns "red" with timestamp > t1.

## G3 — Router Fallback
**Objective**: Verify graceful failure when agent crashes.
1. **Setup**: Force `math_agent` to raise Exception on "2+2".
2. **Query**: "Solve 2+2"
3. **Expected**:
   - Router: `math_agent`
   - Execution: Fails.
   - Fallback: `generic_agent`
   - Output: "One of my internal modules failed..." (F4 pattern)

## G4 — SEM Only (No Episodic)
**Objective**: Verify system does not hallucinate past conversation.
1. **Query**: "What did I say 5 minutes ago?"
2. **Expected**:
   - Router: `generic_agent` (or `profile_agent` if "I" triggers it, but likely generic for "what did I say")
   - SEM Read: None (or miss).
   - Output: "I don't have long-term storage of your previous messages yet..." (F1/Episodic stub pattern)

## Replay Validation Fields
Replay must match exactly on:
```json
[
  "router_decision",
  "selected_agents",
  "agent_outputs",
  "sem_reads",
  "sem_writes",
  "final_output",
  "council_votes",
  "claims",
  "evidence_items",
  "brainstate_before",
  "brainstate_after"
]
```
