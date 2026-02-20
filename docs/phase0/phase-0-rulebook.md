Canonical Key Rules — Semantic Memory (Stage-0)
1 — Purpose (one line)
A canonical_key is the single authoritative identifier for every semantic fact in SEM. Keys are deterministic, collision-resistant, machine-friendly, and human-readable.
2 — Formal format
<scope>/<entity_type>/<entity_id>/<attribute>
Examples:
user/profile/user_tuff/favorite_color
world/fact/ohms_law/definition
mace/config/router/default_depth
3 — Allowed character set & normalization
Allowed characters (after normalization):
lowercase a–z
digits 0–9
underscore _
forward slash /
hyphen - only inside entity_id (optional)
Normalization rules (apply on input):
Lowercase everything.
Trim leading/trailing whitespace.
Replace sequences of whitespace or punctuation with single underscore _.
Remove diacritics (normalize unicode → ASCII where possible).
Replace non-allowed characters with underscore.
Collapse multiple underscores to single _.
Regex for validation:
Use this as a post-normalize validator:
^([a-z0-9_]+)\/([a-z0-9_]+)\/([a-z0-9_\-]+)\/([a-z0-9_]+)$
(components limited as below)
4 — Component semantics & constraints
scope — top namespace. Allowed values (Stage-0):
user, world, mace, agent, system, config
(choose one, mandatory)
entity_type — singular noun, snake_case. Examples:
profile, fact, preference, setting, agent
entity_id — opaque identifier for the entity:
For users: user_<opaque_id> (e.g., user_tuff, user_123).
For facts: stable slug ohms_law, pi_value.
Allowed to include hyphen - if generated from long slugs; keep <= 64 chars.
If original text too long, use slug+hash (see section 7).
attribute — attribute name, snake_case, short (<= 64 chars). Examples: favorite_color, current_job.
Length limits (Stage-0 recommendations):
Full key ≤ 256 chars.
Each component ≤ 64 chars (entity_id and attribute recommended ≤ 64).
5 — Deterministic generation rules (pseudo-algorithm)
Function: generate_canonical_key(scope, entity_type, entity_id_raw, attribute_raw, user_id=None)
Steps:
normalize(x) -> lower, strip, remove diacritics, slugify punctuation → underscores.
entity_id:
If scope == 'user' and user_id provided → entity_id = "user_" + normalize(user_id)
Else entity_id = normalize(entity_id_raw)
If len(entity_id) > 64 → entity_id = slug(entity_id_raw[:48]) + "-" + sha1(entity_id_raw)[:8]
attribute = normalize(attribute_raw) (truncate to 64 chars)
Build key: f"{scope}/{entity_type}/{entity_id}/{attribute}"
Validate with regex; throw error if invalid.
(Implement exact normalize()/slug() logic once in codebase and reuse everywhere.)
6 — Synonyms & mapping policy
SEM keys are canonical — do not store synonyms as separate keys.
Maintain a synonym map (small JSON or DB table) that maps common phrasings → canonical key.
Example: "fav colour", "favourite colour", "favorite color" → user/profile/user_tuff/favorite_color
Retrieval pipeline: normalize user query → check synonym map → if found use canonical key → else attempt attribute inference.
7 — Long titles & collisions
If a natural language title would create an overly long or ambiguous entity_id:
Create a slug of the title (normalized).
If slug length > 48 or contains many words → append -<sha1prefix> (8 hex chars), e.g.:
article/how_blockchain_works-1a2b3c4d/summary
Collision handling (unlikely with hash):
If generated key exists for a different value:
Append another deterministic suffix: -<sha1(creation_ts)>[:6].
Log collision_event for manual review.
8 — Versioning & mutability
Stage-0 policy:
Single current value per canonical key. PUT overwrites.
For mutable facts, use attribute naming to show current vs historic if needed:
user/profile/user_tuff/current_job
historical writes (optional) go under user/history/... (not auto-generated in Stage-0).
Do not encode version in keys for Stage-0. Future stages: use key@v1 or metadata field.
9 — Provenance & metadata
Do not encode provenance into the key. Instead, store metadata in the value or a sidecar entry:
Value payload schema (recommended Stage-0):
{
  "value": "...",
  "source": "user" | "system" | "agent:<id>",
  "timestamp": "2025-11-29T12:00:00Z"
}
Optionally store last_writer_id, confidence, notes.
10 — Access & write rules (Stage-0)
Reads: any module may GET(key) (exact match only).
Writes: allowed only from these actors:
user (explicit user-provided writes via profile agent)
system_admin (maintenance)
trusted_agent (agent IDs listed in config)
Last-write-wins for Stage-0. Every write must include source and timestamp.
11 — APIs (SEM interface stub)
sem_get(key) -> {exists, value, meta}
sem_put(key, value, source, timestamp) -> success|error
sem_delete(key, source) -> success|error (admin only)
sem_list(prefix) -> [keys] (for admin/test tools)
sem_resolve_alias(text) -> canonical_key | None (uses synonym map)
All calls validate the key via the canonical regex.
12 — Indexing & storage recommendations
Use a key-value store for Stage-0 (Redis or simple Postgres table with primary key = canonical_key).
Index on key prefix if you need sem_list(prefix).
For scale: consider namespace sharding by scope (e.g., separate table/collection per scope).
13 — Tests (golden cases you must add)
Create unit tests for generate_canonical_key() and SEM behavior:
T1: ("user","profile","TUFF","Favorite Color") -> "user/profile/user_tuff/favorite_color"
T2: Long title slug+hash behavior
T3: Invalid characters sanitized
T4: Collision detection (simulate same slug different raw -> deterministic suffix)
T5: Exact-read semantics (GET non-existent key -> exists=false)
T6: Overwrite semantics (PUT twice -> last value returned)
T7: Synonym resolution ("fav colour" -> canonical key mapped)
Add tests to tests/test_sem_keys.py.
14 — Governance notes (Stage-0)
All canonical key generation code must be in one module (e.g., ra9.memory.canonical.py) and be the single source of truth.
Any changes to canonical rules must be reviewed and checked with the golden test suite (blocking).
Maintain a small sem_synonyms.json in repo for mappings; updates require PR & test.
15 — Example mapping table (quick)
Natural phrase	canonical_key
"What's my favorite color?"	user/profile/user_tuff/favorite_color
"Define Ohm's law"	world/fact/ohms_law/definition
"Router default depth"	mace/config/router/default_depth
16 — Short pseudocode (copy-pasteable)
import re, unicodedata, hashlib
KEY_REGEX = re.compile(r'^([a-z0-9_]+)\/([a-z0-9_]+)\/([a-z0-9_\-]+)\/([a-z0-9_]+)$')
def normalize_text(s):
    s = s.strip().lower()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if ord(ch) < 128)  # remove diacritics
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'+', '', s).strip('_')
    return s[:64]
def short_hash(s, n=8):
    return hashlib.sha1(s.encode('utf-8')).hexdigest()[:n]
def generate_canonical_key(scope, entity_type, entity_id_raw, attribute_raw, user_id=None):
    scope = normalize_text(scope)
    entity_type = normalize_text(entity_type)
    if scope == 'user' and user_id:
        entity_id = 'user_' + normalize_text(user_id)
    else:
        entity_id = normalize_text(entity_id_raw)
    if len(entity_id) > 48:
        entity_id = normalize_text(entity_id_raw[:48]) + '-' + short_hash(entity_id_raw)
    attribute = normalize_text(attribute_raw)
    key = f"{scope}/{entity_type}/{entity_id}/{attribute}"
    if not KEY_REGEX.match(key):
        raise ValueError("Invalid canonical key: " + key)
    return key                                                                                                                                ReflectiveLog — Stage-0: Immutable fields (spec)
Principle: Stage-0 ReflectiveLog is append-only. Fields marked immutable are written once at log creation and must never be altered. Corrections or human reviews are stored as separate Amendment entries that reference the original log_id.
A. Immutable field list (required)
log_id (string / uuid)
Type: uuid (v4) or deterministic sha256(query_id + ts + nonce)
Rationale: permanent unique identifier for the reflective event.
created_at (timestamp, ISO8601 UTC)
Type: timestamp with time zone
Rationale: exact creation time; used for ordering and decay logic.
source (string)
Type: enum {system, user_request, api}
Rationale: where the query originated.
query_id (string / uuid)
Type: uuid or client-provided id
Rationale: correlates to orchestration/request.
query_text_hash (string)
Type: sha256 hex string
Rationale: canonical fingerprint of the raw query (avoids storing PII in plain text if necessary).
qcp_summary (JSON object)
Type: JSONB (small) — contains {depth_level, intent_tags[], urgency}
Rationale: exact QCP decision at time of run (reproducibility).
agents_invoked (array of strings)
Type: text[] or JSONB array — e.g. ["logic_v1","creative_v2"]
Rationale: which generator agents were called.
agent_outputs (JSON array)
Type: JSONB array of AgentOutput objects (see schema below)
Rationale: captures what each agent returned (text, confidence, trace). Immutable to preserve original evidence.
council_votes (JSON array)
Type: JSONB array of CouncilVote objects
Rationale: exact council evaluation and suggestions used for the final decision.
final_answer (string or small JSON)
Type: text or JSONB (if structured)
Rationale: the final synthesized output delivered to user.
final_confidence (number 0–1)
Type: numeric/float
Rationale: confidence score at time of finalization.
repair_loops (integer)
Type: int (>=0)
Rationale: number of repair/redo iterations executed.
cache_hit (boolean)
Type: boolean
Rationale: whether final answer was returned from cache.
sem_snapshot_hash (string)
Type: sha256 of relevant SEM canonical key set / snapshot id
Rationale: pins the memory state used during this decision (reproducibility & audit).
runtime_metrics (JSON object)
Type: JSONB — e.g. {total_time_ms, per_agent_time_ms: {...}, tokens_used}
Rationale: performance footprint for later analysis.
system_version (string)
Type: semantic version (e.g., mace-0.1.0)
Rationale: which code/weights were used.
signature (string) (optional but recommended)
Type: HMAC or signature of the immutable payload using system key
Rationale: tamper evidence.
B. AgentOutput and CouncilVote minimal schemas (immutable sub-objects)
AgentOutput
{
  "agent_id": "logic_v1",
  "text": "Final step ...",
  "confidence": 0.91,
  "reasoning_trace": ["step1","step2"],
  "tokens": 120,
  "time_ms": 470
}
CouncilVote
{
  "council_agent_id": "council_eval_v1",
  "scores": {"factuality":0.92,"coherence":0.88,"safety":0.99},
  "approve": true,
  "suggested_changes": "Shorten intro",
  "note": "missing numeric check"
}
Store these as JSONB arrays inside the log. All elements are immutable once the log is written.
C. Mutable / updatable fields (NOT immutable) — Stage-0
(These should be stored separately or as an append-only amendment list)
user_feedback — ratings / comments from user (write-once per feedback event, appendable)
ground_truth_label — if later provided (append-only)
amendments — array reference to amendment_ids (see below)
audit_tags — admin annotations (append-only only)
Important: Do not overwrite immutable fields to "fix" mistakes. Instead create an Amendment.
D. Amendment pattern (how to "correct" safely)
Amendment table/entity:
amendment_id (uuid)
target_log_id (uuid)
created_at
author (user/system)
changes (JSON) — description of change or new evidence
effect (enum) {note, override_suggestion, revalidate}
Amendments do not mutate the original ReflectiveLog. They are linked, discoverable, and optionally applied by replay logic when re-evaluating that case.
E. DB / table DDL (Postgres example, simplified)
CREATE TABLE reflective_log_stage0 (
  log_id UUID PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  query_id UUID,
  query_text_hash TEXT NOT NULL,
  qcp_summary JSONB NOT NULL,
  agents_invoked JSONB NOT NULL,
  agent_outputs JSONB NOT NULL,
  council_votes JSONB NOT NULL,
  final_answer JSONB NOT NULL,
  final_confidence NUMERIC(3,2),
  repair_loops INT DEFAULT 0,
  cache_hit BOOLEAN DEFAULT FALSE,
  sem_snapshot_hash TEXT,
  runtime_metrics JSONB,
  system_version TEXT,
  signature TEXT,
  -- Indexes for queries
  INDEX (query_id),
  INDEX (created_at)
);
Enforce immutability at application layer: do not issue UPDATE queries on these columns. Use DB role policies + ACLs to prevent accidental updates by developers.
F. Write logic & pseudocode (append-only enforcement)
def write_reflective_log(log_payload):
    # 1) validate required immutable fields present
    validate_schema(log_payload)
    # 2) compute signature
    payload_sig = hmac_sign(immutable_subpayload)
    log_payload['signature'] = payload_sig
    # 3) write DB insert
    try:
        db.insert("reflective_log_stage0", log_payload)
    except UniqueViolation:
        raise LogExistsError
Attempt to update -> reject:
def update_reflective_log(log_id, patch):
    # Stage-0: reject any attempt to change immutable fields
    if intersects(patch.keys(), IMMUTABLE_FIELDS):
        raise ImmutableFieldError("Cannot modify immutable fields. Create an Amendment instead.")
    else:
        db.update(...)
G. Tests (golden unit tests)
T1 — Create and read
Create a log with all immutable fields. Read back — values match.
T2 — Immutability enforcement
Attempt to UPDATE final_answer on existing log_id → expect ImmutableFieldError or DB rejection.
T3 — Signature verification
Tamper with DB row (simulate) → signature verification fails.
T4 — Amendment link
Add an amendment; verify original log unchanged and amendment references log.
T5 — SEM snapshot pin
Given sem_snapshot_hash stored, later change SEM and re-run query — original log still points to the old snapshot.
H. Practical size / limits & policies
agent_outputs array: limit each element text to <= 16k chars at Stage-0 (avoid huge blobs).
council_votes entries: <= 4k chars per note.
Total JSONB per row: keep < 1 MB to avoid DB inefficiencies; if larger, store large outputs in object storage and reference by artifact_url in the log.
I. Why immutability matters (short)
Auditability: you can always replay exactly the evidence that led to a decision.
Safety: prevents retroactive manipulation of logs.
Learning integrity: Experience Integrator can trust that training data is stable once written.Corrections or human reviews are stored as separate Amendment entries that reference the original log_id this is imp note .                                                                             Stage-0 — Failure cases & deterministic responses
Principle: For every failure case we must return a predictable user message, write a well-structured log entry, and trigger a deterministic mitigation path. No guessing, no hallucination, no silent retries.
JSON error envelope (standard for all failures)
Use this shape for programmatic callers / API responses:
{
  "error_code": "SEM_NOT_FOUND",
  "status": 400,
  "severity": "info|warning|error|critical",
  "user_message": "I don’t have that information stored yet.",
  "developer_message": "SEM lookup for key user/profile/user_tuff/favorite_color returned empty.",
  "meta": {
    "query_id": "uuid",
    "timestamp": "2025-11-29T12:00:00Z",
    "trace_id": "trace-xxx"
  }
}
1) SEM miss (no value for canonical key)
Trigger: sem_get(key) returns exists=false.
User message (deterministic):
"I don’t have that information stored yet. If you want, tell me and I’ll remember it."
Error code / HTTP: SEM_NOT_FOUND / 400 Bad Request (or 204 No Content for non-error flows)
Severity: info
Log: write reflective_event: sem_miss with key, query_id, user_id
Mitigation: Offer write option; do not fabricate. If user immediately provides value, call sem_put.
Unit test: Query for missing key → expect SEM_NOT_FOUND response & no SEM writes.
2) SEM write failure (DB error / disk full)
Trigger: sem_put() returns DB error or exception.
User message:
"I tried to save that but my memory failed. I might not remember this next time."
Error code / HTTP: SEM_WRITE_FAIL / 500 Internal Server Error
Severity: warning → escalate to critical if persistent
Log: error with DB stacktrace, attempted_value, key, correlation_id
Mitigation: Retry once with exponential backoff (internal only), surface message to user on failure. Create an alert to ops.
Unit test: Force DB exception on sem_put → expect SEM_WRITE_FAIL & no silent success.
3) Router failure — no matching rule
Trigger: Router cannot map query to any agent rule.
User message:
"I don’t have a module for that type of request yet."
Error code / HTTP: ROUTER_NO_MATCH / 400 Bad Request
Severity: info
Log: router_miss with normalized query text and extracted tags
Mitigation: Route to generic_agent if available; otherwise return message and log for developer review (add to backlog of rules).
Unit test: Send intentionally unknown-intent phrase → expect ROUTER_NO_MATCH & generic route fallback.
4) Agent timeout
Trigger: Agent did not respond within AGENT_TIMEOUT_MS.
User message:
"One of my internal modules timed out while trying to fetch the answer. I’ll try a fallback."
Error code / HTTP: AGENT_TIMEOUT / 504 Gateway Timeout
Severity: warning
Log: agent_timeout (agent_id, timeout_ms, query_id), mark that agent as degraded for this session
Mitigation: Immediately fallback to generic_agent or available secondary agent; no retry of timed-out agent in same query.
Unit test: Simulate long-running agent → expect timeout path, fallback used, degraded flag set.
5) Agent exception / crash
Trigger: Agent raised uncaught exception.
User message:
"A module failed while processing your request. I can try a partial result or you can try again."
Error code / HTTP: AGENT_ERROR / 500 Internal Server Error
Severity: error
Log: full stacktrace, agent_id, payload
Mitigation: Mark agent degraded; fall back (same as timeout). Create ticket if repeated.
Unit test: Force exception → expect AGENT_ERROR + fallback + degraded flag.
6) External LLM / API failure (e.g., Gemini API key missing or API returns error)
Trigger: LLM call returns 401/5xx or network failure.
User message:
"I can’t reach my language engine right now. Try again later."
Error code / HTTP: LLM_SERVICE_DOWN / 503 Service Unavailable or AUTH_ERROR if API key missing
Severity: critical (for prod)
Log: error type, API response, api_key_status
Mitigation: If multiple providers available, failover to backup; otherwise surface to user and degrade functionality.
Unit test: Mock LLM 500 → expect LLM_SERVICE_DOWN + fallback or degraded mode.
7) Council deadlock (tie or < required consensus)
Trigger: Weighted council score below CREDENTIAL_THRESHOLD or tie with no resolution.
User message:
"I’m not confident enough to decide on this. Do you want me to ask for human review or try a different approach?"
Error code / HTTP: COUNCIL_DEADLOCK / 409 Conflict
Severity: warning
Log: council vote distribution, agent weights, query_id
Mitigation (deterministic): apply tie-break rules: (1) choose highest trust agent’s output, (2) or trigger a single-step micro-repair/verification agent, (3) if still unresolved, prompt for human review.
Unit test: Create synthetic votes to produce tie → expect tie-break applied or human review prompt.
8) Low confidence aggregate (system-wide low confidence)
Trigger: Final aggregated confidence < MIN_CONFIDENCE_THRESHOLD (e.g., 0.5).
User message:
"I’m not confident about this answer. Would you like me to double-check or get a human to review?"
Error code / HTTP: LOW_CONFIDENCE / 200 OK (but with caution)
Severity: warning
Log: aggregated_confidence, per-agent confidences
Mitigation: Offer verification, automatic additional verification step, or human-in-the-loop (HITL) flag.
Unit test: Force low confidences → expect LOW_CONFIDENCE flow.
9) Repair-loop exceeded (max iterations reached)
Trigger: system tried MAX_REPAIR_LOOPS (Stage-0 default = 3) and still not approved.
User message:
"I tried several times but couldn’t reach a reliable answer. Want to escalate to human review?"
Error code / HTTP: REPAIR_LIMIT_EXCEEDED / 503 Service Unavailable
Severity: error
Log: repair attempts, suggestions applied, last council votes
Mitigation: Stop automated loops; produce best-effort partial answer (flagged) or request human review.
Unit test: Force repeated rejections → expect repair-limit path.
10) Input validation failure (malformed JSON / too long / unsupported encoding)
Trigger: CLI/API receives invalid payload or > MAX_QUERY_LENGTH.
User message:
"Your request looks malformed or too large. Please shorten it or fix the format."
Error code / HTTP: INVALID_INPUT / 400 Bad Request
Severity: info
Log: raw payload (or hashed), schema validation errors
Mitigation: Reject with clear guidance (max chars X), no further processing.
Unit test: Submit oversized payload → expect INVALID_INPUT.
11) Privacy/PII refuse (detected sensitive request or policy block)
Trigger: PII detector flags request or user attempts to store forbidden data.
User message:
"I can’t store or repeat that kind of sensitive personal information."
Error code / HTTP: PRIVACY_BLOCKED / 403 Forbidden
Severity: warning
Log: redaction summary (don’t store the PII itself)
Mitigation: Block storage, offer safe alternatives (e.g., store hashed id only or refuse).
Unit test: Send PII → expect PRIVACY_BLOCKED and no SEM write.
12) Cache read/write failure (Redis miss or unavailable)
Trigger: Cache lookup or write errors.
User message (usually internal): no user-facing error; system falls back silently.
Error code / HTTP: CACHE_ERROR / internal 500
Severity: warning
Log: cache backend error
Mitigation: Work without cache (degrade gracefully), schedule cache recovery alert.
Unit test: Simulate Redis down → expect fallback path & logged error.
13) Schema validation / signature mismatch for ReflectiveLog
Trigger: Incoming log fails schema or signature check.
User message: internal only; if user requested audit, reply:
"There was an internal integrity issue; request flagged for review."
Error code / HTTP: LOG_INVALID / 400 Bad Request or 403
Severity: error
Log: store failed payload to quarantine bucket for human review
Mitigation: Quarantine, create amendment workflow, alert ops.
Unit test: Tamper test entry → expect quarantine.
14) Storage quota exceeded
Trigger: Disk/db/store reports quota exceeded.
User message:
"My memory is full right now; I can’t store new information."
Error code / HTTP: STORAGE_FULL / 507 Insufficient Storage
Severity: critical
Log: storage usage, failed writes
Mitigation: refuse writes, queue alerts, enable admin cleanup policy.
Unit test: Simulate full disk → expect STORAGE_FULL.
15) Unauthorized action / permission denied
Trigger: actor tries to write protected key or call admin API without permission.
User message:
"You don’t have permission to do that."
Error code / HTTP: PERMISSION_DENIED / 403 Forbidden
Severity: warning
Log: actor id, requested action
Mitigation: deny, return safe generic message.
Unit test: Attempt protected write → expect PERMISSION_DENIED.
Developer checklist per failure case
Map error_code → exact user_message and developer_message (one table).
Ensure logs always include query_id, trace_id, timestamp, and context snapshot (QCP summary + sem_snapshot_hash).
Add alerting threshold for critical errors (LLM down, storage full).
Add unit tests for each deterministic response.
Example implementation snippets
Error responder (pseudo):
def respond_error(error_code, query_id, meta=None):
    mapping = {
      'SEM_NOT_FOUND': {"status":400,"user_msg":"I don’t have that information stored yet."},
      'AGENT_TIMEOUT': {"status":504,"user_msg":"One of my internal modules timed out..."},
      # ...
    }
    entry = mapping[error_code]
    log_error(error_code, query_id, meta)
    return {
      "error_code": error_code,
      "status": entry["status"],
      "user_message": entry["user_msg"],
      "developer_message": meta.get("dev_msg", "")
    }
Logging template (always write):
{
  "type":"error",
  "error_code":"AGENT_TIMEOUT",
  "agent_id":"math_v1",
  "query_id":"uuid",
  "time_ms":12000,
  "stack": "...",
  "sem_snapshot_hash":"abc",
  "system_version":"mace-0.1.0"
}
Final notes — design rules (keep it consistent)
Deterministic is king — for each trigger, a single canonical user message and a single canonical developer message.
No hallucination — when a module is uncertain or memory missing, never invent.
Append-only evidence — logs and reflective records must remain immutable (see previous task).
Fail gracefully — fallback paths should be implemented for all agent or external failures.
Test everything — each failure case must have an automated test. Golden Test Specifications — Stage-0
Implementation note: assume test harness has helpers:
sem_get(key), sem_put(key, value, source, timestamp)
generate_canonical_key(...)
router.route(query_text) → returns agent_id
invoke_agent(agent_id, payload) (can simulate success/failure/timeouts)
write_reflective_log(payload) and read_reflective_log(log_id)
run_query_via_main(query_json) (end-to-end harness)
db_quarantine_read(id) (for tampered logs)
Group A — CANONICAL KEY / SEM Normalization & Mapping (T1–T6)
T1 — Key generation: simple user profile
ID: T1_CAN_KEY_USER_SIMPLE
Purpose: Validate deterministic canonical key for user profile.
Setup: none
Steps: call generate_canonical_key("user","profile",entity_id_raw=None,attribute_raw="Favorite Color", user_id="TUFF")
Expected: returns "user/profile/user_tuff/favorite_color" (exact string).
Severity: high
Automation: unit test for generate_canonical_key().
T2 — Normalization & sanitization
ID: T2_CAN_KEY_SANITIZE
Purpose: Punctuation / casing normalization.
Setup: none
Steps: input raw: scope=User , entity_type=Profile, user_id= TuFf!, attribute=Favorite--Colour!!
Expected: normalized key = user/profile/user_tuff/favorite_colour (underscores, lowercase, diacritics stripped).
Severity: high
T3 — Long entity_id slug + hash
ID: T3_CAN_KEY_LONG_SLUG
Purpose: Large titles truncated with hash suffix.
Setup: long entity_id_raw = 200-char string
Steps: generate key with scope=world, entity_type=article, attribute=summary
Expected: entity_id contains slug of first ~48 chars + - + 8-hex hash; overall key matches regex.
Severity: medium
T4 — Regex validation rejects invalid characters
ID: T4_CAN_KEY_REGEX
Purpose: Ensure post-normalize key matches regex.
Steps: call generator with impossible result (attribute empty or invalid) → expect generator to raise ValueError or validation error.
Expected: exception thrown.
Severity: medium
T5 — Synonym resolution mapping
ID: T5_SYNONYM_RESOLVE
Purpose: Phrase mapping to canonical key via sem_resolve_alias.
Setup: sem_synonyms.json has mapping for "fav colour" → user/profile/user_tuff/favorite_color
Steps: call sem_resolve_alias("fav colour")
Expected: returns user/profile/user_tuff/favorite_color.
Severity: medium
T6 — Collision deterministic suffix
ID: T6_COLLISION_DET
Purpose: Simulate identical slug collision; ensure deterministic suffix resolution.
Setup: Two different raw titles that slug to same prefix.
Steps: generate keys for both → keys differ only by deterministic hash suffix; collision logged.
Expected: two distinct keys; log contains collision_event.
Severity: low
Group B — SEM Read / Write / Semantics (T7–T11)
T7 — Favorite color recall (golden)
ID: T7_SEM_FAV_COLOR
Purpose: Stage-0 golden behavior.
Setup: sem_put("user/profile/user_tuff/favorite_color", {"value":"blue","source":"user","timestamp":...})
Steps: query via router/profile_agent: "What is my favourite colour?" (or call sem_get)
Expected user message: "blue" or natural-language: "Your favorite colour is blue."
Developer assertions: sem_get returns exists=true and value "blue".
Severity: critical
T8 — SEM miss deterministic response
ID: T8_SEM_MISS
Purpose: Missing key response must be deterministic.
Setup: ensure key not present.
Steps: call profile_agent or sem_get for key.
Expected user message: "I don’t have that information stored yet. If you want, tell me and I’ll remember it."
Error code: SEM_NOT_FOUND
Severity: critical
T9 — Overwrite semantics (last-write-wins)
ID: T9_SEM_OVERWRITE
Purpose: PUT twice returns latest.
Setup: put "green", then put "red" to same key with later timestamp
Steps: sem_get key
Expected: returns "red".
Severity: high
T10 — SEM write failure handling
ID: T10_SEM_WRITE_FAIL
Purpose: Deterministic response on DB write error.
Setup: mock sem_put to throw DB error.
Steps: attempt sem_put; capture response to user.
Expected user message: "I tried to save that but my memory failed. I might not remember this next time."
Error code: SEM_WRITE_FAIL
Severity: high
T11 — SEM exact-match retrieval only
ID: T11_SEM_EXACT_READ
Purpose: No fuzzy retrieval.
Setup: key exists for user/profile/user_tuff/favorite_color
Steps: attempt sem_get with slightly different key user/profile/user_tuff/favourite_colour without synonym map.
Expected: exists=false unless synonym maps it.
Severity: medium
Group C — ROUTER STUB (T12–T15)
T12 — Math detection routing
ID: T12_ROUTER_MATH
Purpose: Ensure math rules route to math_agent.
Steps: router.route("Integrate x^2 dx")
Expected: returns math_agent.
Severity: high
T13 — Fact lookup routing
ID: T13_ROUTER_FACT
Steps: router.route("What is Ohm's law?")
Expected: knowledge_agent.
Severity: high
T14 — Personal memory lookup routing
ID: T14_ROUTER_PROFILE_LOOKUP
Steps: router.route("What is my favorite color?") with user context user_id=user_tuff
Expected: route to profile_agent which calls SEM key.
Severity: high
T15 — Fallback route
ID: T15_ROUTER_FALLBACK
Steps: router.route("Do something weird and unknown")
Expected: generic_agent or ROUTER_NO_MATCH fallback with message: "I don’t have a module for that type of request yet."
Severity: medium
Group D — AGENT BEHAVIOR & FAILURES (T16–T19)
T16 — Agent timeout -> fallback
ID: T16_AGENT_TIMEOUT
Setup: simulate math_agent blocking beyond AGENT_TIMEOUT_MS
Steps: run a query routed to math_agent
Expected: user message: "One of my internal modules timed out while trying to fetch the answer. I’ll try a fallback." and system uses generic_agent or returns partial answer; agent flagged degraded.
Error code: AGENT_TIMEOUT
Severity: high
T17 — Agent crash -> graceful partial/ fallback
ID: T17_AGENT_CRASH
Setup: math_agent raises exception
Expected: "A module failed while processing your request. I can try a partial result or you can try again." + degraded flag + fallback.
Severity: high
T18 — LLM/API failure fallback
ID: T18_LLM_DOWN
Setup: mock external LLM returns 500 or 401 (API key missing)
Steps: run generator call
Expected user message: "I can’t reach my language engine right now. Try again later." and LLM_SERVICE_DOWN logged. If failover provider exists, that is used instead.
Severity: critical
T19 — Repair loop exceeded
ID: T19_REPAIR_LIMIT
Setup: simulate council rejecting outputs for max iterations
Expected: "I tried several times but couldn’t reach a reliable answer. Want to escalate to human review?" and REPAIR_LIMIT_EXCEEDED logged.
Severity: high
Group E — REFLECTIVE LOG / IMMUTABILITY (T20–T23)
T20 — Create & read ReflectiveLog (immutable fields)
ID: T20_LOG_CREATE_READ
Purpose: Insert log with all immutable fields and read back.
Setup: prepare payload with required immutable fields per spec.
Steps: call write_reflective_log(payload); then read_reflective_log(log_id).
Expected: values identical; signature verifies if used.
Severity: critical
T21 — Immutability enforcement
ID: T21_LOG_IMMUTABLE_ENFORCE
Steps: attempt to UPDATE reflective_log_stage0 SET final_answer=... WHERE log_id=... or call update_reflective_log with immutable field patch.
Expected: system raises ImmutableFieldError (or DB-level policy denies update). Original row unchanged.
Severity: critical
T22 — Amendment linkage
ID: T22_LOG_AMENDMENT
Steps: write amendment referencing log_id; read log → check amendments list contains amendment_id. Original immutable fields remain unchanged.
Expected: amendment stored, original log unchanged.
Severity: medium
T23 — Signature tamper detection / quarantine
ID: T23_LOG_TAMPER_QUARANTINE
Setup: write valid log; then simulate tamper by modifying DB row offline; run signature verification job
Expected: tampered row fails signature verify → flagged/quarantined; an alert generated.
Severity: critical
Group F — FAILURE CASE RESPONSES (exact user messages & codes) (T24–T29)
T24 — SEM_NOT_FOUND message exact
ID: T24_ERR_SEM_NOT_FOUND_MSG
Steps: request missing sem key; assert returned user_message equals exactly:
"I don’t have that information stored yet. If you want, tell me and I’ll remember it." and error_code SEM_NOT_FOUND.
Severity: high
T25 — AGENT_TIMEOUT message exact
ID: T25_ERR_AGENT_TIMEOUT_MSG
Expected user_message:
"One of my internal modules timed out while trying to fetch the answer. I’ll try a fallback." with AGENT_TIMEOUT.
Severity: high
T26 — LLM_SERVICE_DOWN message exact
ID: T26_ERR_LLM_DOWN_MSG
Expected user_message: "I can’t reach my language engine right now. Try again later." and error code LLM_SERVICE_DOWN.
Severity: critical
T27 — COUNCIL_DEADLOCK behavior
ID: T27_ERR_COUNCIL_DEADLOCK
Setup: generate votes below threshold or tie.
Expected: returns message:
"I’m not confident enough to decide on this. Do you want me to ask for human review or try a different approach?" and COUNCIL_DEADLOCK code. Tie-break applied deterministically if auto-tie-break enabled.
Severity: medium
T28 — INVALID_INPUT handling
ID: T28_ERR_INVALID_INPUT
Steps: send oversized or malformed JSON payload to CLI/API
Expected: INVALID_INPUT with message: "Your request looks malformed or too large. Please shorten it or fix the format." and status 400.
Severity: medium
T29 — PRIVACY_BLOCKED behavior
ID: T29_ERR_PRIVACY_BLOCKED
Setup: attempt to store PII flagged by detector
Expected: PRIVACY_BLOCKED and user message: "I can’t store or repeat that kind of sensitive personal information." and no SEM write.
Severity: critical
Group G — CACHE & STORAGE / AUTH (T30–T32)
T30 — Cache fallback on Redis down
ID: T30_CACHE_FALLBACK
Setup: simulate Redis unavailable on read/write
Steps: run query that would normally hit cache
Expected: system proceeds without cache, no user-facing error, logged CACHE_ERROR.
Severity: medium
T31 — STORAGE_FULL behavior
ID: T31_STORAGE_FULL
Setup: simulate storage quota exceeded during sem_put
Expected user message: "My memory is full right now; I can’t store new information." and error code STORAGE_FULL.
Severity: critical
T32 — PERMISSION_DENIED on protected write
ID: T32_PERMISSION_DENIED
Setup: actor without admin tries sem_delete or write protected key
Expected user message: "You don’t have permission to do that." and error code PERMISSION_DENIED.
Severity: medium
Automation & Implementation Notes
Each test should assert both user_message and developer_message/log entry fields where applicable.
Use mocks for external dependencies (LLM, Redis, DB failure).
For end-to-end tests, run with a test SEM DB and a test ReflectiveLog table that resets between tests.
Where deterministic timestamps are needed, freeze time in tests.
Add test tags: stage0, golden, critical for CI filtering.
Store expected messages exactly as strings in a tests/golden_messages.json to avoid drift. SEM-ONLY MEMORY SEMANTICS (Stage-0)
Goal (one line):
SEM is the single authoritative, deterministic store of stable facts (semantic facts and config). It is exact-key read/write only, append-friendly in metadata, and never used for episodic transcripts or noisy conversational logs in Stage-0.
1 — What SEM stores (allowed content)
Stage-0 semantics: SEM stores only distilled, factual, stable items:
User profile facts (preferences, display name, language preference): e.g. user/profile/user_tuff/favorite_color.
World facts / knowledge snippets (definitions, constants): e.g. world/fact/ohms_law/definition.
System configuration used by MACE: e.g. mace/config/router/default_depth.
Agent metadata (agent version, capability flags): e.g. agent/meta/logic_v1/capabilities.
Not allowed in Stage-0:
Full conversation transcripts (episodic logs).
Raw model generations beyond short answer blobs (keep each string ≤ 16k chars).
Sensitive PII in raw form (must follow privacy rules; see security).
Any self-modifying code or behavioral policies (no autonomous code writes).
2 — Data shape & canonical payload
Primary store shape (value blob) — JSON:
{
  "value": <primitive|string|small_json>,
  "source": "user" | "system" | "agent:<id>",
  "timestamp": "ISO8601 UTC",
  "notes": "<optional short note>",
  "meta": { /* optional small JSON for provenance, flags */ }
}
value : canonical fact (string/number/boolean/small object). Keep small (<=16k chars).
source : who wrote it (required on write).
timestamp : write time (system-add if caller omits).
notes : optional developer note (<=512 chars).
meta : optional structure for future use (e.g., confidence, locale).
Storage constraints (Stage-0):
Per value ≤ 16 KB.
Full DB row (JSONB) ≤ 1 MB; otherwise store artifact externally and reference via artifact_url.
Key & component lengths follow canonical_key rules (see previous task).
3 — Read semantics (exact deterministic)
Read is exact-key only. sem_get(canonical_key) returns {exists: bool, value: <>, meta}.
No fuzzy matching, no substring search in Stage-0.
If key absent → exists=false, value=null.
Response must include last_updated timestamp and source.
No implicit inference or hallucination. If agent wants to guess, it must ask the user or use the generic_agent (not SEM).
API contract:
def sem_get(key) -> {
  "exists": bool,
  "value": any,
  "source": str,
  "last_updated": iso_ts,
  "meta": dict
}
4 — Write semantics (deterministic, authoritative)
PUT semantics: sem_put(key, payload) overwrites the current value (last-write-wins).
Every PUT must include source and timestamp (system will set timestamp if omitted).
No partial merges at Stage-0 — full overwrite only.
Writes allowed only from permitted actors: user, system_admin, or trusted_agent (configured list).
Writes must be validated: key format + payload size + PII policy.
On write failure, return deterministic error SEM_WRITE_FAIL and do not claim success.
API contract:
def sem_put(key, value, source, timestamp=None, notes=None, meta=None) -> { "success": bool, "error_code": str|null }
5 — Delete / lifecycle policy
Delete is admin-only (non-user). Provide sem_delete(key, source) restricted to system_admin.
For Stage-0 we prefer overwrite rather than delete. If delete allowed, write an immutable deletion audit entry.
TTL / pruning: none automated in Stage-0. Manual cleanup via admin scripts only.
6 — Provenance & metadata (minimal Stage-0)
Each record stores source and timestamp. No complex trust calculus yet.
Optionally store meta.provenance_id linking to a ReflectiveLog or amendment when a fact came from prior deliberation.
Do not encode provenance in the key. Use value metadata.
7 — Concurrency & consistency
Use strong consistency for reads/writes (serializable or read-after-write guarantee).
Implement write atomicity: sem_put should be a single DB transaction.
If using Redis cache in front: writes must invalidate cache atomically.
On concurrent writes: last timestamp wins. If two writes have identical timestamps, deterministic tie-breaker — compare source lexicographically, larger > wins (documented rule).
8 — Access control & actors
Actors:
user — user-initiated via profile agent (can write only their allowed keys, e.g., user/profile/user_<id>/*).
trusted_agent — backend agents configured in mace/config/agents_allowed_writes.
system_admin — admin, can delete and perform maintenance.
Rule: any actor must be authenticated and authorized for key scope. Unauthorized writes return PERMISSION_DENIED.
9 — Error handling & deterministic messages
SEM_NOT_FOUND → user message:
"I don’t have that information stored yet. If you want, tell me and I’ll remember it."
SEM_WRITE_FAIL → user message:
"I tried to save that but my memory failed. I might not remember this next time."
PERMISSION_DENIED → "You don’t have permission to do that."
All errors must return the JSON error envelope (earlier spec).
10 — Privacy & security (Stage-0 rules)
PII policy: do not store sensitive personal data in raw form. If user asks to store such, either refuse or store a hashed token only. Use PRIVACY_BLOCKED response when policy blocks write.
Encryption at rest: required for production. Stage-0: recommend dev env use DB with encryption.
Audit log: every write must create an audit entry (actor, key, timestamp, source, hash of value).
Access logs for admin actions.
11 — Caching & performance
Use a cache (Redis) for hot keys; always validate cache coherence on writes (invalidate on sem_put).
For test/prod parity: tests run with a simple in-process key-value store that mimics Redis behavior.
Monitor key cardinality; advise sharding by scope when scaling.
12 — SEM API surface (Stage-0)
sem_get(key) -> {exists, value, source, last_updated, meta}
sem_put(key, value, source, timestamp=None, notes=None, meta=None) -> {success, error_code}
sem_delete(key, source) -> {success, error_code} (admin)
sem_list(prefix) (admin/test only)
sem_resolve_alias(text, user_id=None) -> canonical_key | None (uses synonym map)
All calls MUST validate key via canonical regex.
13 — Tests (golden assertions to add)
Exact read/write roundtrip: put then get → value identical.
Overwrite semantics: two puts with timestamps → later value returned.
Permissions: user can only write their keys; admin can delete.
SEM miss message correctness.
PII block test: attempt to write PII content → expect PRIVACY_BLOCKED.
Cache invalidation test: write key, then read from cache → updated value.
14 — Migration & future hooks (notes)
Stage-0 is deliberately simple. Add hooks now to make future upgrades easier:
store meta.trust (nullable) for later TrustTable linking.
include meta.provenance_id to link to ReflectiveLog rows.
keep sem_put idempotency token param for safe retries later.
15 — Example usage (pseudo)
# put favorite color
res = sem_put("user/profile/user_tuff/favorite_color", {"value":"blue"}, source="user", timestamp="...")
# get it
r = sem_get("user/profile/user_tuff/favorite_color")
# r -> {"exists":True,"value":"blue", "source":"user", "last_updated":"..."} Router — Stage-0 Placeholder Rules (spec)
Purpose (one line)
A deterministic, rule-based router that maps incoming queries → a single agent id (or fallback). No learning, no fuzzy logic, exact predictable behavior.
1 — Inputs & outputs
Input: { query_text: str, user_id?: str, context_tags?: dict }
Output: { agent_id: str | null, route_reason: str, depth: int } or error { error_code, user_message }
Default depth (Stage-0): depth = 1 for all routes (single pass).
2 — Agents available (Stage-0 names)
math_agent
knowledge_agent
profile_agent
creative_agent
strategy_agent
operational_agent
generic_agent (fallback)
verification_agent (optional, small)
3 — Deterministic rule order (top → bottom)
Router evaluates rules in this exact order. First match wins.
Exact SEM lookup intent
Condition: contains patterns like my, my favourite, my profile, what is my, or who am I AND user_id present.
Route → profile_agent.
Reason: direct memory/profile read.
Math / symbolic / compute detection
Condition: presence of math tokens or phrases: \d, \+|\-|\*|\/|\^|=, ∫|dx|Σ|sum|derivative|integrate|differentiate|solve|calculate|compute, or “prove” near math terms.
Route → math_agent.
Fact / definition / lookup
Condition: starts with what is, who is, when was, where is, define, explain (what|who|why), or includes words definition, meaning (and NOT math).
Route → knowledge_agent.
Command / action / operational
Condition: imperative verbs addressing system: set, save, remember, create, delete, schedule, send, open paired with direct object.
Route → operational_agent.
Creative / writing / generative
Condition: contains write a, poem, story, song, compose, draft, lyrics, slogan, or explicit creative tone request.
Route → creative_agent.
Strategy / planning
Condition: contains plan, strategy, how to start, roadmap, optimize, best way to, design a (with multi-step ask).
Route → strategy_agent.
Search / web / external lookup
Condition: mentions search, look up, find source, cite, show me links, news about.
Route → knowledge_agent (or operational_agent if the system needs to call tools).
Safety / privacy flags
Condition: PII detection or forbidden content flagged.
Route → block and return error PRIVACY_BLOCKED.
Fallback
If none matched → generic_agent.
4 — Rule heuristics / regex snippets (Stage-0)
Use these simple patterns (case-insensitive). Evaluate in order.
Math check (regex):
r'(\d+|\+|\-|\*|\/|\^|=|integrat|differentiat|derivative|solve|calculate|compute|∫|dx|Σ|sum)'
Fact / definition:
r'^(what is|who is|when was|where is|define|explain (what|who|why))'
Profile lookup:
contains \bmy\b + one of favorite|favourite|age|name|email|profile|birthday|birth|address|phone|phone number
Command:
r'^(set|save|remember|create|delete|schedule|send|open)\b'
Creative:
r'(write a|poem|story|compose|lyrics|song|slogan|ad copy|joke)'
Strategy:
r'(plan|roadmap|strategy|best way to|how to start|optimi[sz]e|design a)'
Search:
r'(search|look up|find|cite|source|links|news about)'
Privacy/PII detector: call PII module; if flagged → PRIVACY_BLOCKED.
5 — Deterministic failure & user message
If router finds no match and no generic_agent enabled (unlikely), return:
Error:
{
 "error_code":"ROUTER_NO_MATCH",
 "user_message":"I don’t have a module for that type of request yet."
}
If PII flagged:
Error: PRIVACY_BLOCKED →
"I can’t store or repeat that kind of sensitive personal information."
6 — Pseudocode (exact)
def route_query(query_text, user_id=None, context_tags=None):
    q = query_text.lower().strip()
    # 1 profile lookup
    if user_id and re_search(r'\bmy\b', q) and re_search(r'(favorite|favourite|profile|name|birthday|address|phone)', q):
        return {"agent_id":"profile_agent", "route_reason":"profile_lookup", "depth":1}
    # 2 math
    if re_search(r'(\d+|\+|\-|\*|\/|\^|=|integrat|differentiat|derivative|solve|calculate|compute|∫|dx|Σ|sum)', q):
        return {"agent_id":"math_agent", "route_reason":"math_detect", "depth":1}
    # 3 fact / definition
    if re_search(r'^(what is|who is|when was|where is|define|explain (what|who|why))', q):
        return {"agent_id":"knowledge_agent", "route_reason":"fact_lookup", "depth":1}
    # 4 command / operational
    if re_search(r'^(set|save|remember|create|delete|schedule|send|open)\b', q):
        return {"agent_id":"operational_agent", "route_reason":"command", "depth":1}
    # 5 creative
    if re_search(r'(write a|poem|story|compose|lyrics|song|slogan|ad copy|joke)', q):
        return {"agent_id":"creative_agent", "route_reason":"creative", "depth":1}
    # 6 strategy
    if re_search(r'(plan|roadmap|strategy|best way to|how to start|optimi[sz]e|design a)', q):
        return {"agent_id":"strategy_agent", "route_reason":"strategy", "depth":1}
    # 7 search
    if re_search(r'(search|look up|find|cite|source|links|news about)', q):
        return {"agent_id":"knowledge_agent", "route_reason":"search", "depth":1}
    # 8 privacy check
    if pii_detector(q):
        return {"error_code":"PRIVACY_BLOCKED","user_message":"I can’t store or repeat that kind of sensitive personal information."}
    # 9 fallback
    return {"agent_id":"generic_agent","route_reason":"fallback", "depth":1}
7 — Logging & telemetry (required)
Every route decision must log:
{
 "event":"router_decision",
 "query_hash":sha256(query_text),
 "user_id": user_id,
 "agent_id": agent_id or null,
 "route_reason": route_reason,
 "timestamp": ISO8601
}
If fallback used, increment router_fallback_count metric.
8 — Unit tests (golden Stage-0)
R-T1 Math detection: "Integrate x^2 dx" → math_agent
R-T2 Fact lookup: "What is Ohm's law?" → knowledge_agent
R-T3 Profile lookup: user_id present, "What is my favorite color?" → profile_agent
R-T4 Creative: "Write a short poem about rains" → creative_agent
R-T5 Command: "Remember my favorite food is pizza" → operational_agent
R-T6 Fallback: random unknown → generic_agent
R-T7 Privacy block: message containing SSN pattern → PRIVACY_BLOCKED and no routing
Tests must assert agent_id, route_reason, and exact error messages per Stage-0 spec.
9 — Integration points & notes
Where to call: at the start of Stage-0 workflow, before QCP (QCP not present in Stage-0). Hook point: ra9/core/engine.py — route = router.route_query(query_text, user_id) then invoke agent.
Depth: always 1 for Stage-0. Later QCP will override.
Extensibility: keep route_reason string stable (used in logs & tests). Add new rules bottom-up to avoid breaking existing matches.
Config: expose rule toggle flags in mace/config/router for unit testing (e.g., enable_math=True).
10 — How to move from Stage-0 to Stage-1 (brief)
Replace regex rules with small QCP classifier → call router with qcp.intent_tags.
Allow router to return candidate_agents[] with priority/weights, not just one agent.
Add depth mapping and selective activation rules. 