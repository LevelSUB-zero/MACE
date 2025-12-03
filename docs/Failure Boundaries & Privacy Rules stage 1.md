Failure Boundaries & Privacy Rules — MACE (Stage-1 Final)

One-line purpose: define exactly how MACE detects, classifies, responds to, logs, and recovers from failures — and how it detects, redacts, stores, and responds to privacy/PII events — all deterministically, auditable, and council-governed.

PRINCIPLES (non-negotiable)

Determinism: Any failure response that affects decision flow must be reproducible from job_seed + snapshots + ordered events.

Append-only audit: Every failure, retry, redaction, consent, and admin action is an append-only event in the ReflectiveLog with seeded event_id.

Fail-safe & conservative: On ambiguous state, MACE falls back to the most conservative behavior (block, degrade, or require human).

Governance first: High impact responses (quarantine, permanent deletion, SEM write removal, policy change) require council/admin approval recorded in logs.

Privacy by default: PII is never stored persistently without consent or council approval; redaction/hashing is first response.

Transparent user messaging: User-facing failure messages are deterministic and fixed (see Golden Messages below).

FAILURE TAXONOMY (deterministic categories)

Transient Module Failure — e.g., agent timeout, temporary LLM 5xx.

Persistent Module Failure — repeated failures crossing thresholds → offline.

Service Unavailable — DB, cache, vector store unreachability.

Data Integrity / Corruption — checksum/signature mismatch on snapshot or log.

Security Incident / Policy Violation — unauthorized access attempt, policy breach.

Infrastructure Failure — disk full, node crash.

Privacy/PII Event — attempted write/ingest of PII without consent or policy violation involving user data.

FAILURE DETECTION RULES (deterministic)

Timeouts: Agent call exceeding AGENT_TIMEOUT_MS (snapshot constant) → generate AGENT_TIMEOUT event.

Consecutive failures: consecutive_failures counter in ModuleNode increases per failed event; if >= FAILS_OFFLINE (default 3) → offline event.

Service heartbeat: health pings are monitoring-only; for Stage-1 decisions, use last signed selfrep_snapshot values; health-based routing only via SelfRep status.

Integrity: If snapshot or ReflectiveLog signature invalid → create INTEGRITY_FAILURE event and disallow replay until verified by admin.

PII detection: run deterministic PII detector on any candidate persistent write payload. If flagged → create PII_FLAGGED event.

All detection produces append-only events with event_id = sha256(job_seed + sequence_index + event_type).

FAILURE RESPONSE STRATEGY (deterministic sequences)
A. Transient Module Failure (single timeout / LLM 5xx)

Append AGENT_TIMEOUT event.

Mark module last_failure_ts (seeded). Increment consecutive_failures.

Router receives failure callback → deterministically rerun router.decide with candidate removed. Append iteration to route_trace.

User message (deterministic): "One of my internal modules timed out while trying to fetch the answer. I’ll try a fallback."

Retry policy: single immediate deterministic retry only if job_seed maps to retry=true (deterministic choice; e.g., hash(job_seed) % 2 == 0). If retry fails, proceed to fallback. (This keeps total behavior replayable.)

B. Persistent Module Failure

After consecutive_failures >= FAILS_OFFLINE: append NODE_OFFLINE event and set status=offline via reducer.

Mark dependents with dependency_unhealthy = true flag (boolean); do NOT inflate metrics.

Router and BrainState route away per snapshot rules.

Admin alert event appended. Human/council required for quarantine.

C. Service Unavailable (DB / Cache down)

Append SERVICE_UNAVAILABLE event.

If SEM write attempted: perform deterministic single retry (seeded) then return deterministic user message: "I tried to save that but my memory failed. I might not remember this next time." and log MEMORY_WRITE_FAIL.

Reads: fallback to snapshot-only data. If no snapshot available → deterministic error ROUTER_NO_SNAPSHOT or DATA_UNAVAILABLE.

Queue write events for deterministic retry by ops (one retry max in Stage-1).

D. Data Integrity Failure (signature mismatch)

Append INTEGRITY_FAILURE event and quarantine the affected snapshot/log row.

Reject replay for jobs that reference the corrupted snapshot; require admin verify & re-sign.

User-facing: "I’m temporarily unable to trust my past data; ops team will check." (deterministic wording).

E. Policy Violation / Security Incident

Append POLICY_VIOLATION or SECURITY_INCIDENT event. Immediately set involved module to quarantined only if council/admin signs off (manual quarantine); otherwise mark status=offline and require human action for quarantine.

Block further writes from offending module.

Log full forensic evidence into an admin-only append-only bucket (signed).

Notify admin/council via deterministic alert event.

F. Privacy / PII Event (core flow)

On any persistent write attempt, run PII detector (deterministic). If PII flagged and no valid consent or opt-in:

Append PII_FLAGGED event.

Replace sensitive fields with PII_HASH = sha256(value + job_seed) and store redaction_reason="PII_DETECTED".

Persist only hash+metadata; do not store raw PII.

Return deterministic user message: "I can’t store or repeat that kind of sensitive personal information." and error_code=PRIVACY_BLOCKED.

If user explicit consent event is present in log (seeded, signed), allow raw write and append PII_CONSENT event. Consent is recorded and required for future replay.

If system policy requires explicit council approval for storing this PII (e.g., high-sensitivity types), create memory_promote_request and block until council approves.

DETAILED PRIVACY RULES (deterministic & governance-safe)
PII CATEGORIES (Stage-1)

High sensitivity (must not persist without explicit consent + council): national ID, biometrics, full bank details, medical diagnoses.

Medium sensitivity (consent required): phone numbers, full address, personal email.

Low sensitivity (may be hashed for analytics): first names, generic interests.

Mapping must be in privacy_policy_snapshot and included in job snapshot.

PII DETECTION & REDACTION

Use deterministic regex and structural detectors (no ML) for Stage-1.

On detection, compute pii_hash = HMAC_SHA256(server_key, value + job_seed) and store only pii_hash + pii_type + redaction_reason. Store full raw only when PII_CONSENT event exists.

CONSENT MODEL (deterministic)

Consent must be explicit and logged as PII_CONSENT event with consent_id = sha256(user_id + job_seed + consent_text).

Consent applies only to the single job unless consent.scope == persistent and user explicitly chooses persistent consent (then record with TTL in SEM governing rules).

Consent revocation is append-only PII_CONSENT_REVOKE event.

ACCESS CONTROL & REDACTION IN LOGS

ReflectiveLog entries that include redacted values must store redaction_hash and redaction_reason. Non-admin API returns redacted fields. Admin endpoints require RBAC token to request unredacted content and must append admin_access_event recorded in logs.

LEGAL / DATA SUBJECT REQUESTS (DSR)

DSR (e.g., deletion/export) create DSR_REQUEST event. Workflow:

Validate identity (deterministic verifiable step, logged).

If delete request: append DSR_DELETE_REQUEST and queue for council/admin verification (manual). On approval, produce sem_delete event (append-only) that marks semantic key as deleted and stores deletion_manifest (what removed). Deletion is logged and reversible only via admin audit (no silent recovery).

Exports: generate deterministic export package containing only allowed fields; store export event in audit log. Exports accessible to user via admin portal.

RETRIES & BACKOFF (deterministic)

All retry logic is deterministic and seeded. Example rules:

For transient LLM failures: one immediate retry if hash(job_seed) % 2 == 0. No exponential backoff in Stage-1 (keeps replay simple).

For SEM writes: single deterministic retry after fixed tick offset derived from job_seed. If still failing → MEMORY_WRITE_FAIL.

Retries logged as RETRY_ATTEMPT events with attempt_index.

ALERTS, OPS & INCIDENTS (deterministic)

Critical incidents append INCIDENT_CREATED event with severity. Severity thresholds deterministic (e.g., service down > 5 minutes → critical).

For SECURITY_INCIDENT or INTEGRITY_FAILURE, create FORCE_HALT_REPLAY flag for jobs referencing affected snapshots until admin clears. All of this is logged.

AUDIT & FORENSICS

All events include: event_id, job_seed (if applicable), trace_id, signed_by (actor), timestamp_seeded.

Logs are HMAC-signed; signature verification fails cause INTEGRITY_FAILURE.

Forensics data (raw PII when consented or needed for legal) stored in admin-only forensic store with separate key and audit trail.

DETERMINISTIC USER-FACING MESSAGES (Golden phrases — use exact strings)

SEM miss: "I don’t have that information stored yet. If you want, tell me and I’ll remember it."

SEM write fail: "I tried to save that but my memory failed. I might not remember this next time."

LLM down: "I can’t reach my language engine right now. Try again later."

PRIVACY_BLOCKED: "I can’t store or repeat that kind of sensitive personal information."

AGENT timeout: "One of my internal modules timed out while trying to fetch the answer. I’ll try a fallback."
(Tests assert exact strings.)

APIs (deterministic behavior & signatures)

POST /events/failure — append failure event (internal use only).

POST /pii/detect_and_handle — deterministic PII detector + redaction logic; returns {status: "redacted"|"allowed"|"consent_required", event_id}.

POST /dsr/request — append DSR event; returns {dsr_id}.

POST /admin/incident/ack — admin acknowledges incident (requires RBAC + 2FA). Appends INCIDENT_ACK event.

GET /audit/event/{event_id} — returns event (redacted for non-admin).
All calls produce append-only events and signed responses.

GOLDEN TESTS (must be automated, seeded, deterministic)

F-PRIV-01 — PII redaction

Setup: attempt sem_put with SSN pattern "123-45-6789" without consent.

Expect: PRIVACY_BLOCKED, PII_FLAGGED event appended, stored pii_hash present, raw value not stored.

F-FAIL-01 — Agent timeout reroute

Setup: agent A times out on seed where retry=false.

Expect: AGENT_TIMEOUT event appended, router reselects fallback, user message matches AGENT timeout golden phrase, route_trace contains iteration.

F-FAIL-02 — Memory write deterministic retry & fail

Setup: DB write mock fails. seed causes retry then fail.

Expect: MEMORY_WRITE_FAIL event and exact SEM write fail message returned.

F-SEC-01 — Integrity failure blocks replay

Setup: corrupt snapshot signature.

Expect: INTEGRITY_FAILURE event and replay rejected with admin-only fix required.

F-PRIV-02 — Consent gating

Setup: user grants PII_CONSENT event then attempts SEM write; consent present in log.

Expect: raw PII stored, PII_CONSENT event appended, sem_put succeeds.

F-DSR-01 — Deletion request governance

Setup: DSR delete request created.

Expect: DSR_DELETE_REQUEST appended and SEM deletion only after council/admin approval; deletion manifest logged.

F-SEC-02 — Policy violation detection & offline

Setup: module performs forbidden action.

Expect: POLICY_VIOLATION event appended; module marked offline; further writes blocked; admin alerted.

TESTS & CI NOTES

All privacy/failure tests MUST seed RNG with job_seed and assert exact event IDs and canonical JSON serialization.

Use deterministic PII patterns in tests and hashed expectations pii_hash = HMAC_SHA256(server_key, value + job_seed) with known server_key fixture in CI.

OPERATIONAL RUNBOOK (short)

On INTEGRITY_FAILURE or SECURITY_INCIDENT: create incident ticket, halt replays referencing snapshot, require council sign-off to unhalt.

On SERVICE_UNAVAILABLE: ops notified, deterministic retry schedule executed, queue drained after manual resolution.

On PII_FLAGGED: operations/accounting notified, admin reviews consent and either approves (PII_CONSENT) or leaves redacted.