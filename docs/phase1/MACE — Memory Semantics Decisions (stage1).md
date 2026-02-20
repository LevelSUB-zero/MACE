MACE — Memory Semantics Decisions (Stage-1 Final)

One-line purpose:
Define exactly what each memory layer stores, how it changes, how retrieval works, how promotion works, privacy & governance constraints, and deterministic APIs + golden tests — all in a way that preserves replayability and auditability.

0 — High-level rules (always)

Deterministic — any decision-reading memory during a job must be reproducible from snapshots + job_seed. No live telemetry affects behavior.

Snapshots — every job records sem_snapshot_id, episodic_snapshot_id (if used), and brainstate_snapshot_id in the ReflectiveLog. Replay loads these snapshots.

Append-only events — memory writes are append-only events. No silent in-place overwrites except when explicitly allowed by governance (and then still recorded).

Governance for persistent SEM writes — SEM writes require either explicit user intent or an ActionRequest that was council-approved (Stage-1 default).

PII first — run PII detector before any persistent write; redact or refuse per policy.

TTL = ticks — time-to-live for WM/CWM measured in deterministic workflow ticks (not wall clock).

1 — Memory layers (definitions & purpose)
A. WM — Working Memory (ephemeral)

Purpose: Short-lived items used within the current reasoning episode (e.g., user hints, intermediate facts, small context bits).

Representation: ordered list, newest-first. Each WM entry:

{
 "wm_id":"wm:<job_seed>:<counter>",
 "type":"fact|context|hint|temp",
 "value": <JSON-serializable>,
 "created_at_tick": 5,
 "ttl_ticks": 3,           // integer, default 3
 "references": 1           // incremented deterministically when referenced
}


Behavior:

Inserted during job by agents/router/BrainState via deterministic calls.

On each brainstate.tick(), all ttl_ticks decremented; remove entries with ttl_ticks <= 0.

references increments deterministically when the item is used by an agent/decision.

Promotion to CWM: if references >= PROMOTION_REFERENCES within PROMOTION_WINDOW ticks (both snapshot constants), the item is promoted to CWM (see CWM rules).

Persistence: WM never written to SEM automatically. At job end, certain WM items can create an Episodic Event (see below) deterministically.

B. CWM — Consolidated Working Memory (short-term stable)

Purpose: Short-lived, consolidated context used for multi-step reasoning within and across closely related jobs (like a session). Not yet SEM.

Representation:

{
 "cwm_id":"cwm:<session_or_job_seed>",
 "topic":"<string>",
 "items":[ { "cwm_id_item":"...", "value":..., "promoted_from_wm": true } ],
 "token_estimate": 512
}


Behavior:

CWM items are added only via deterministic promotion from WM (no freeform writes).

CWM size limited deterministically by token_estimate (snapshot value).

CWM is recomputed deterministically when promotions happen or when a new major goal starts.

On job end, CWM may be persisted as an episodic summary (append-only) but not as SEM unless an ActionRequest is approved.

TTL & decay: CWM entries carry ttl_ticks_cwm (e.g., default 10 ticks) decremented per tick if not re-referenced. Promotion back to WM on heavy use is allowed but must be deterministic.

C. Episodic Memory (append-only event store)

Purpose: Durable record of experiences, interactions, decisions, and reflective logs — used later for retrieval, auditing, and offline analysis.

Representation (episodic_entry):

{
 "episodic_id":"ep:<uuid-seeded>",
 "job_seed":"seed-xxx",
 "source":"agent|executor|brainstate",
 "summary":"short text",
 "evidence": [ { "sem_keys": [...], "sem_snapshot_hash":"..." } ],
 "payload": { ... full structured event ... },
 "created_seeded_ts":"...",   // derived from job_seed
 "provenance": { "trace_id":"...", "reflective_log_id":"..." }
}


Behavior:

Written append-only when job ends, on ActionRequests, or when agents request episodic writes (deterministic).

Queryable by deterministic retrieval functions (see Retrieval).

Can be used to generate ActionRequests for SEM promotion (human/council gating).

D. SEM — Semantic (stable facts)

Purpose: Canonical store of distilled stable facts (canonical_key → value). Stage-0 rules from earlier apply.

Key rule for Stage-1: No automatic promotion from episodic/CWM to SEM. Any change to SEM must be via:

explicit user action (user says "remember X"), OR

ActionRequest appended + council/admin approval recorded in ReflectiveLog.

PII & policy: Existing SEM PII rules apply (PII detector; redaction; consent).

2 — Deterministic promotion rules (WM → CWM → Episodic → SEM)
WM → CWM (automatic, deterministic)

Trigger when:

A WM entry’s references >= PROMOTION_REFERENCES within PROMOTION_WINDOW ticks (both stored in brainstate_snapshot). Default: PROMOTION_REFERENCES=2, PROMOTION_WINDOW=4.

Action:

Move entry into CWM (remove from WM).

Append promotion_event to module_state_events with seeded event_id.

Update cwm.items deterministically (keep token budgets).

Replays: promotions re-executed from the same tick traces.

CWM → Episodic (automatic at job end)

At job end, deterministic summary of CWM is written as episodic_summary (append-only). Summary includes sem_snapshot_hash and reflective_log_id.

This is not SEM.

Episodic → SEM (manual & governed)

To convert episodic knowledge to SEM:

Create memory_promote_request action (ActionRequest) automatically (agent) or by user.

ActionRequest appended to ReflectiveLog with justification and evidence links.

Council/admin review required; upon approval, sem_put is executed deterministically and logged.

Rationale: prevents accidental long-term writes & respects governance.

3 — Retrieval semantics (deterministic, Stage-1)

General rule: Retrieval functions produce deterministic ranked lists using only snapshot-sourced data + deterministic scoring.

SEM retrieval

sem_get(canonical_key): exact-match only (Stage-0 behavior). Returns {exists, value, meta}.

sem_search(prefix): deterministic prefix listing; must use canonicalization function. No fuzzy search.

Episodic retrieval (deterministic relevance)

episodic_query(query_terms, window_n, max_results):

Tokenize query_terms deterministically (simple lower-case split on whitespace & punctuation).

For each episodic entry, compute overlap = count_matching_terms(entry_summary_tokens, query_tokens).

Score = overlap / max(1, len(entry_summary_tokens)) — deterministic normalisation.

Rank by (score desc, created_seeded_ts desc) deterministic tie-breakers: lexicographic episodic_id.

Supports time_window filters by created_seeded_ts.

No vector similarity or ML at Stage-1.

CWM/WM lookup

Agents query by wm_find(predicate) or cwm_find(predicate) where predicate is a deterministic structural matcher (exact keys, exact values, or key existence). No fuzzy matching.

Evidence linking

Any retrieval result returned in decision must include evidence which contains episodic_id and sem_snapshot_hash used. All evidence written back into ReflectiveLog.

4 — APIs & function signatures (deterministic)

wm_insert(job_seed, entry) → returns wm_id; appends deterministic event to job trace.

brainstate.tick() handles WM TTL decrement and promotions.

cwm_get(snapshot_id) read-only for job.

episodic_write(job_seed, summary, payload, evidence) → append-only; returns episodic_id.

episodic_query(query_tokens, max_results, snapshot_id) → returns deterministic ranked list.

memory_promote_request(episodic_id, target_sem_key, justification, evidence) → appends ActionRequest to ReflectiveLog (awaits council).

sem_put(canonical_key, value, source) — only executed on explicit user request or council-approved ActionRequest. Follows SEM Stage-0 PII rules.

All calls record trace_id and are append-only when writing.

5 — PII & Redaction (deterministic)

Before any persistent write (episodic or SEM promotion), run PII detector.

If PII flagged and user consent absent → redact sensitive fields (store hash + metadata) and write an PII_REDACTED event. Do not fail the write unless the user explicitly requested storing raw PII (requires explicit consent event logged).

Episodic summaries used in retrieval must return redacted versions to non-admin callers. Full payload accessible only to admin/council endpoints.

ReflectiveLog entries referencing redacted content must store only hash and redaction_reason.

6 — Determinism & replay requirements (exact)

All tick counts, promotions, and episodic ids must be derived deterministically from job_seed and ordered event counters (no random UUIDs unless seeded).

sem_snapshot_hash computed as sha256(sorted list of (key + canonical_serialized_value + timestamp_seeded)). Save the exact hash string in the snapshot. Use canonical JSON serialization (keys sorted, predictable float format) to ensure reproducibility.

When replaying, load the same snapshots and event stream; re-run brainstate.tick() steps to reproduce WM→CWM promotions and episodic writes.

7 — Storage schemas (Stage-1 minimal)
Episodic table (Postgres JSONB)
CREATE TABLE episodic_stage1 (
 episodic_id TEXT PRIMARY KEY,
 job_seed TEXT,
 created_seeded_ts TEXT,
 summary TEXT,
 payload JSONB,
 evidence JSONB,
 provenance JSONB
);

WM / CWM (in-memory per job; optional persisted per session)

WM stored in memory during job lifecycle; for replay, WM events saved in ReflectiveLog trace.

SEM (as per previous Stage-0 schema)
8 — Golden tests (must be in Stage-1 CI)

M-T1 — WM TTL & removal

Insert WM with ttl_ticks=2, run two ticks, expect removal.

M-T2 — WM→CWM promotion

Insert WM item, reference it twice within PROMOTION_WINDOW=4 ticks, expect it present in CWM and removed from WM.

M-T3 — CWM→Episodic on job end

With CWM items present, end job, expect an episodic_summary appended containing CWM snapshot.

M-T4 — Episodic deterministic retrieval

Create several episodic entries seeded; query with deterministic tokens; assert ranked list matches expected order.

M-T5 — Memory promotion gating (ActionRequest)

Create episodic entry; call memory_promote_request; ensure ActionRequest appended and no SEM write until council approval. After simulated approval, ensure sem_put executed deterministically.

M-T6 — PII redaction enforced

Attempt to promote episodic with PII; expect redaction event and stored hash; SEM write only with user consent + logged event.

M-T7 — Replay reproduces promotions & episodic writes

Run job with seeded events that cause promotions & episodic writes; replay with same seed → expect identical event sequence & episodic ids.

M-T8 — Storage full / write fail deterministic response

Simulate DB write error on episodic_write → expect MEMORY_WRITE_FAIL deterministic error envelope and queued retry behavior (one deterministic retry only).

9 — Failure boundaries & mitigations

MEMORY_WRITE_FAIL (DB down): retry once with deterministic backoff (derived from job_seed), then return deterministic user-facing message: "I tried to save that but my memory failed. I might not remember this next time." (same as SEM write failure). Log trace & alert ops.

STORAGE_FULL: return STORAGE_FULL error, do not silently drop data. Append event to queue for admin.

PII_BLOCKED: refuse raw storage and produce deterministic PRIVACY_BLOCKED message.

PROMOTION_LOOP: promotions are idempotent by design; if promotion event already exists for (wm_id), reject duplicate (idempotency check).

10 — Governance & admin controls

ActionRequest flow for any persistence→SEM: append request → council review → explicit approval event → sem_put execution (all logged).

Admin-only reads: full episodic payloads and unredacted snapshots require admin role. Non-admins receive redacted versions.

Audit retention: episodic and promotion events immutable for policy-defined retention (e.g., 90 days). Deletion requires council + admin and is recorded as a deletion_event (append-only).

11 — Performance & infra notes (practical)

Episodic: use Postgres JSONB with index on created_seeded_ts and summary token column (simple tokenized text stored as sorted array for deterministic retrieval). No vector DB in Stage-1.

WM/CWM in-memory per executor for performance; snapshot events stored to ReflectiveLog for replay.

Limit episodic query window by max_results and prefilter by time window to bound compute. Deterministic top-N prefiltering: sort by (score desc, created_seeded_ts desc, episodic_id asc) and take first N.

12 — Example flow (deterministic walk-through)

User: “Remember my favourite color is cerulean.” → system asks confirm → user confirms → create memory_promote_request (ActionRequest) with evidence and created_seeded_ts. Append to ReflectiveLog.

Council reviews and approves (or user explicit action may allow direct sem_put). On approval, sem_put("user/profile/user_tuff/favorite_color","cerulean",source=agent) executed deterministically; SEM write logged.

Later query: sem_get("user/profile/user_tuff/favorite_color") returns exact-match "cerulean".

Alternate: For quick session facts, agents store in WM; repeated references promote to CWM; job end writes episodic summary for future retrieval; no SEM change unless ActionRequest approved.