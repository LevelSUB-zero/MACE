# STAGE-0 RULEBOOK — MACE v0.0.1

## Scope of Stage-0

Only Semantic Memory (SEM) is “real” memory.
No episodic, no reflective, no long council loops yet.
Router is a dumb but deterministic stub (rule-based).
Goal of Stage-0 = predictable behavior, not “smartest mind”.

## 1. Semantic Memory (SEM) — canonical_key rules

**Objective:**
Every stable fact must be stored under a canonical_key so we don’t duplicate or clash.

### 1.1 Canonical Key Format

**Rule S1 — Structure**
`<scope>/<entity_type>/<entity_id>/<attribute>`

Examples:
- `user/profile/user_123/favorite_color`
- `world/fact/ohms_law/definition`
- `mace/config/router/default_depth`

**Rule S2 — Allowed character set**
- Lowercase letters a–z
- Digits 0–9
- Underscore _ and forward slash /
- No spaces, no caps, no special chars.

**Rule S3 — Entity & attribute naming**
- `entity_type` is singular, snake_case: user, fact, agent, config
- `attribute` is also snake_case: favorite_color, birth_year, description
- `entity_id`:
    - for user → `user_<opaque_id>`
    - for generic fact → a stable slug: `ohms_law`, `water_boiling_point`.

**Rule S4 — Synonym handling**
SEM must not store synonyms as separate canonical keys.
If multiple phrasings refer to same fact (e.g. “favourite colour”, “color preference”), they map to the same canonical_key, and synonyms are handled at the retrieval layer, not in keys.

Example:
All of these map to the same key:
- “What’s my fav colour?”
- “What color do I like most?”
→ `user/profile/user_123/favorite_color`

**Rule S5 — Versioning**
If a fact can change over time (e.g., current job, current mood), we do:

Current state:
`user/profile/user_123/current_job`

Historical series, if needed:
`user/history/user_123/job/2025_11_10`

Stage-0: we support current state only. Historical is allowed but not required.

## 2. SEM-only Memory Semantics

Stage-0: SEM is the only memory that matters.

### 2.1 What SEM stores

**Rule S6 — SEM stores only stable-ish facts**
- User preferences (favorite color, preferred tone, language).
- World facts (definitions, laws, standard formulas).
- System config & policies (router defaults, thresholds).
- No raw chat logs, no full conversations — just distilled facts.

### 2.2 Read semantics

**Rule S7 — SEM read contracts**
Given a canonical_key, SEM returns:
```json
{
  "exists": true/false,
  "value": <any JSON-serializable>,
  "last_updated": <timestamp>
}
```
If key doesn’t exist → exists=false, value = null.
No fuzzy matching at Stage-0: retrieval is exact by key.

### 2.3 Write semantics

**Rule S8 — Overwrite policy**
PUT canonical_key = value always overwrites the previous value.
No merge, no partial updates at Stage-0.

**Rule S9 — Trust level (Stage-0 simplification)**
For now, SEM doesn’t track multi-source trust; each key has one authoritative value.
Later stages may add provenance and trust; Stage-0 says: last validated write wins.

## 3. Failure Cases & Deterministic Responses

Stage-0 must NEVER behave “mysteriously”. For each failure → fixed, predictable behavior.

### 3.1 Missing memory

**F1 — SEM miss**
Condition: SEM lookup returns exists=false.
Response:
System must not hallucinate a value.
Reply pattern:
“I don’t have this information stored yet.”
And optionally:
“If you want, you can tell me your X so I can remember it for later.”

### 3.2 Conflicting memory (should not exist in Stage-0, but if it does…)

**F2 — Conflict in SEM**
If multiple values somehow exist for one key (data bug), Stage-0 resolves by deterministic rule:
Choose the value with latest last_updated timestamp.
Log a data_integrity_warning for later fixes.

### 3.3 Router failure

**F3 — No agent available / unknown intent**
Condition: Router can’t map intent to an agent (e.g. new task type).
Response:
Fallback agent: `generic_agent` must be used.
If even that fails (not implemented or crashed):
Return error text:
“I currently don’t have a module for this type of request.”

### 3.4 Agent failure

**F4 — Agent crash or timeout**
Condition: an agent doesn’t return within AGENT_TIMEOUT_MS or throws error.
Response:
Mark agent status degraded in runtime log.
Do not call it again in the same query.
Router falls back to `generic_agent` or returns partial answer with explanation:
“One of my internal modules failed while processing this; here is a partial answer based on the remaining modules.”

Stage-0: No automatic retries beyond 1 attempt.

### 3.5 SEM storage error

**F5 — SEM write failure**
Condition: DB error, disk full, etc.
Response:
Do not tell the user “stored successfully” if write failed.
Response pattern:
“I tried to store this, but my memory backend failed. I may not remember this next time.”

## 4. Router Placeholder Rules (Stage-0 Stub)

Router at Stage-0 is dumb but predictable — rule-based, no learning.

### 4.1 Inputs
- query_text
- (Optional) simple tags: is_math, is_emotional, is_fact_lookup.

### 4.2 Rules

**R1 — Math detection**
If query contains explicit math symbols (+, -, *, /, ∫, ∑, dx, ^) or phrases like “solve”, “calculate”, “integrate” →
route to `math_agent`.

**R2 — Fact lookup**
If query starts with “what is”, “define”, “who is”, “when was”, “where is” →
route to `knowledge_agent` (which may use SEM + LLM).

**R3 — Personal memory lookup**
If query contains “my” + one of the known attributes (favorite color, name, etc.) →
route to `profile_agent` which:
First checks SEM (user/profile/...).
If SEM miss, responds with F1 pattern.

**R4 — Fallback**
If none of the above rules matched → route to `generic_agent`.

### 4.3 Depth default (no QCP yet)

Stage-0 depth defaults:
All queries use depth=1 (one-pass reasoning).
No multi-loop reflection in Stage-0, only single shot.

## 5. Stage-0 SEM-only Memory Semantics (more precise)

To “freeze” this:

SEM can:
- Store scalar facts: strings, numbers, booleans.
- Store small JSON blobs (e.g., user profile settings).
- Be queried only via canonical_key.

SEM cannot:
- Do fuzzy search by text.
- Store unstructured long logs (that’s future Episodic).
- Decide what to promote/demote — Stage-0 promotion rules are manual / hardcoded.

**Stage-0 Promotion Rule (stub)**
If we ever simulate “promotion”, it’s via explicit dev code, e.g.:
“After 3 confirmations from user, write to semantic key.”
No automatic background consolidation yet.

## 6. Golden Test Specifications for Stage-0

These are not code, they are the expected behaviors we must pass.

### 6.1 Test G1 — “Favorite color recall”

**Setup:**
Write:
`SEM["user/profile/user_123/favorite_color"] = "blue"`

**Query:**
“What is my favourite colour?”

**Expected behavior:**
Router → `profile_agent`.
SEM lookup → key exists.
Answer: returns “blue” in natural language.
No hallucination, no guessing.

**Negative variant:**
If key doesn’t exist, answer:
“I don’t have your favorite color stored yet.”

### 6.2 Test G2 — “Contradictory evidence → latest wins”

**Setup:**
At t1: write "green" then at t2: write "red" to the same key.

**Query:**
“What is my favourite colour?”

**Expected:**
SEM returns "red" (latest write).
Internally log that multiple historical values existed (if tracked), but Stage-0 returns single deterministic value.

### 6.3 Test G3 — “Fallback router after module failure”

**Setup:**
Configure `math_agent` to throw an error / timeout for a test query.

**Query:**
“Solve 2 + 2.”

**Expected behavior:**
Router → `math_agent`.
`math_agent` fails.
Router detects failure, flags agent as degraded for this request.
Fallback: route to `generic_agent`.
`generic_agent` either:
- solves simple math itself, or
- responds gracefully:
“My math module failed just now; I’m unable to compute this.”

No infinite retries, no crash.

### 6.4 Test G4 — “SEM-only semantics”

**Query:**
“Tell me what I said two turns ago in this conversation.”

**Stage-0 Expected:**
System must NOT pretend to have full conversational episodic memory from DB.
It can only use current context window (whatever the LLM still sees).
If beyond that:
“I don’t have long-term storage of your previous messages yet; I only remember what’s currently in context.”

That enforces: Stage-0 = SEM facts only, not fake long-term memory.

## 7. Safety + Governance (Stage-0 only)

- If SEM is missing → never fabricate personal facts.
- If router fails → default to safe failure message, not random agent.
- No self-modifying behavior at Stage-0 (no module proposals etc.).
- Council is not fully active yet → any “judgement” is internal simple rule, not a multi-agent consensus.
