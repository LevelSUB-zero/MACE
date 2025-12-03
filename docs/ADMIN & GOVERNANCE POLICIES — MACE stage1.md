ADMIN & GOVERNANCE POLICIES — MACE (Stage-1 Final)

One-line purpose:
Define who can change what, how changes are proposed, approved, logged, and replayed — ensuring MACE remains deterministic, auditable, and safe while allowing controlled evolution.

PRINCIPLES (always enforce)

Least privilege: Give actors only the permissions they need. Default = minimal.

Append-only governance: All admin actions are append-only events (GovernanceEvent) stored in ReflectiveLog with seeded event_id. No silent DB mutation allowed.

Deterministic approval semantics: Every approval flow (single-admin, multi-admin quorum, council) is deterministic and recorded with exact participant IDs and seed-derived timestamps.

Replayability: Governance decisions referenced by jobs are part of the snapshot; replay uses the same governance state.

Human-in-loop for risky actions: Any change that affects SEM, module policies, quarantines, or self-modification requires council/admin gating as specified.

Separation of duties: Operational admins vs governance council vs auditors have distinct roles and non-overlapping privileges.

ROLES & AUTHENTICATION
Roles (Stage-1)

Viewer — read-only access to public, non-admin endpoints (can view redacted logs).

Operator — manage day-to-day operations (restart services, view logs, run diagnostics). Cannot change policies or quarantine modules.

Admin — may perform admin actions (register modules, accept low-risk actionrequests, run maintenance). Requires 2FA.

CouncilMember — special governance role. Council actions require ≥COUNCIL_QUORUM (default 3) votes. Council members are small, trusted set.

Auditor — read-only full-access to audit data (unredacted) for a limited retention window; cannot perform admin actions.

SuperAdmin — emergency authority (kill-switch). Use restricted; actions require multi-factor and dual-signature.

Authentication

All role actions require token auth + 2FA for Admin/Council/SuperAdmin.

Tokens are short-lived (configurable) and bound to user_id and role. Use deterministic token issuance logs for audit.

RBAC & Permission Matrix (high-level)

Viewer: read public logs (redacted)

Operator: read logs, start/stop services, health checks

Admin: all Operator + module registration (low impact), accept queued maintenance ActionRequests (non-policy)

CouncilMember: vote on council ActionRequests, approve quarantine, promote high-risk SEM writes, change governance policies

SuperAdmin: emergency halt/resume replays; can temporarily bypass some workflows but must append dual-signed SUPERADMIN_OVERRIDE event and require post-hoc council review.

Exact permission table in governance/permissions.yaml. (Implementers: enforce via middleware.)

GOVERNANCE OBJECTS & DEFINITIONS

GovernanceEvent — append-only event describing governance actions. Fields: event_id (seeded), actor_id, role, action_type, payload, signed=true, signature, job_seed if from a job.

ActionRequest — object created when system or an agent requests a persistent change (SEM write, module policy change, quarantine request, module registration with SEM-write). Fields include request_id, origin, justification, evidence, required_approval_type (single-admin, council-quorum), status.

CouncilVote — {vote_id, request_id, member_id, vote (approve/reject), confidence(optional), signature}. Votes are appended; quorum computed deterministically from snapshot.

GovernancePolicy — system-level config stored in snapshot; changes require PR + council approval.

All governance objects are signed and logged. Use canonical JSON serialization for signature consistency.

ACTION CLASSES & APPROVAL RULES
1. Low-risk actions (single-admin)

Examples: module registration (if module policy forbids SEM-write), routine maintenance toggles, debug logging level changes.

Approval: Admin single-signature. Append ActionRequest with required_approval_type=admin_single. Admin processes via POST /admin/action/approve and event appended.

2. Medium-risk actions (admin + council notification)

Examples: module policy change that adds new allowed actions (but not SEM-write), increasing token budgets beyond snapshot-prescribed limits.

Approval: Admin accepts, but ActionRequest gets auto-notified to council; council votes recorded. A default wait window GOV_APPROVAL_WAIT (snapshot) must pass before effective unless SuperAdmin override used.

3. High-risk actions (council quorum)

Examples: SEM writes promoted by episodic memory, quarantine/unquarantine, module self-modification proposals, governance policy updates, permanent deletion, APT manual overrides for bulk changes.

Approval: Council quorum COUNCIL_QUORUM (default 3) required with recorded votes. Action executed only after quorum achieved and event appended.

4. Emergency actions (SuperAdmin & post-hoc review)

Examples: immediate quarantine of rogue module in active attack, emergency halt of replays for snapshots with integrity failures.

Approval: SuperAdmin dual-signature (SuperAdmin + Admin) allowed; MUST create EMERGENCY_OVERRIDE event and schedule mandatory council review within EMERGENCY_REVIEW_WINDOW (snapshot). Failure to review flags an alert and rollback rules.

ACTIONREQUEST LIFECYCLE (deterministic flow)

Create — any agent, operator, admin, or job can create ActionRequest with seed. POST /actionrequest/create → append-only. Must include evidence (reflective log links) and required_approval_type.

Notify — system notifies required approvers deterministically (email/portal event append-only).

Vote/Approve — approvers append GovernanceEvent or CouncilVote. Votes are recorded with seeded timestamps.

Quorum check — when required votes recorded, system deterministically computes result and updates ActionRequest.status to approved or rejected.

Execute — upon approval, operation executed deterministically and ActionRequest.executed_event appended.

Audit — All steps present in ReflectiveLog and visible to Auditor + Admin with RBAC.

Replay: ActionRequests and their approvals are part of snapshot for jobs referencing them. Replay uses the same approved state.

Timeouts: If ActionRequest doesn’t reach required approvals within ACTIONREQUEST_TIMEOUT (snapshot constant), it transitions to expired. Expiry is append-only.

COUNCIL STRUCTURE & VOTING RULES

Council composition: small, predefined set of CouncilMembers (IDs stored in governance snapshot).

Quorum: default COUNCIL_QUORUM = 3. Configurable but changes require council approval.

Voting weight: equal by default. In future, weighted votes allowed but must be part of snapshot.

Vote types: approve, reject, abstain. abstain counts as non-vote; quorum requires number of votes (approve+reject) >= quorum. Deterministic tie-break: reject wins ties to be conservative.

Deterministic deadlines: voting deadline computed from created_seeded_ts + VOTE_WINDOW (VOTE_WINDOW in snapshot). After deadline, deterministically evaluate votes and mark resolved (approve if majority approve; else reject).

Transparency: All council votes logged in ReflectiveLog. Public view shows only outcome and high-level reason; audit view shows full signed votes.

IMMUTABLE FIELDS & CHANGE MANAGEMENT

Immutable fields (cannot be changed without creating new object and registration entry): node_id, registration.registered_by, registration.registered_at, module.policy.immutable_actions (list). Attempts to mutate these produce ImmutableFieldError GovernanceEvent.

Changing a governance policy (e.g., quorum value) itself requires a high-risk ActionRequest and council approval. Change is applied via new snapshot version and must be included in job snapshots going forward.

SIGNATURES & DETERMINISM

All governance events must include a cryptographic signature: signature = HMAC_SHA256(private_key_of_actor, canonical_serialized_event). Use canonical JSON serializer.

For multi-signature approvals (council), store each signature separately.

Signatures & actor IDs included in ReflectiveLog; replay verifies signatures are present (but in replay mode you may skip signature cryptographic check if snapshot flagged as test-run — still must assert presence).

Deterministic event_id: event_id = sha256(job_seed + actor_id + action_type + sequence_index) for job-origin events; system events use system_seed namespace.

ADMIN APIs (deterministic, signed)

POST /actionrequest/create → append ActionRequest (any role). Returns request_id.

POST /actionrequest/{id}/vote → CouncilMember/Admin votes (signed). Append CouncilVote.

POST /actionrequest/{id}/approve → Admin approves single-admin actions (signed).

POST /governance/policy/propose → propose governance change (ActionRequest, high-risk).

POST /module/register → register module (creates GovernanceEvent). If module requires SEM-write, mark required_approval_type=council_quorum.

POST /module/quarantine → create quarantine request (council required).

GET /governance/events/{event_id} → fetch governance event (redacted for non-admin).

POST /superadmin/override → emergency override (SuperAdmin + Admin signatures needed).

All API calls append governance events and must be included in snapshots for jobs that reference them.

AUDIT, LOG RETENTION & ACCESS

ReflectiveLog is primary audit store. All governance events, ActionRequests, votes, approvals, and signatures stored here.

Retention: governance events immutable for default retention window GOVERNANCE_RETENTION_DAYS (e.g., 365 days) then archived to forensic store with restricted access. Deletion only via council-approved DSR_DELETE_REQUEST logged event.

Auditors: read-only view to full unredacted logs for AUDIT_WINDOW_DAYS (e.g., 90 days) with pre-authorized audit token; all access appended as admin_access_event.

Tamper detection: logs HMAC-signed; verification job runs daily; any mismatch creates INTEGRITY_FAILURE event.

EMERGENCY PROCEDURES & KILL-SWITCH
Kill-switch (SuperAdmin)

Trigger: POST /superadmin/override with both SuperAdmin and Admin signatures. Allowed to HALT_REPLAYS, QUARANTINE_MODULE_IMMEDIATE, FREEZE_SNAPSHOT_REGISTRY. Action appended as EMERGENCY_OVERRIDE.

Post-hoc: Must schedule council review within EMERGENCY_REVIEW_WINDOW (snapshot value). Failure to review triggers automatic alert to auditors and ops.

Replay halt flag: jobs referencing affected snapshots must check FORCE_HALT_REPLAY and abort deterministic replay with INTEGRITY_FAILURE until cleared.

Incident response

SECURITY_INCIDENT events create deterministic runbook steps:

quarantine suspected modules (requires council/admin per rules; superadmin allowed immediate quarantine but logged)

halt new deployments (append event)

generate forensic export to admin-only store

notify ops & council (append-only notifications)

All steps logged and must be part of incident ticket (incident_id).

TESTS & CI for Governance (must exist in Stage-1 CI)

GOV-T1 — ActionRequest lifecycle

Create ActionRequest (seeded), record request_id. Simulate council votes to reach quorum. Assert ActionRequest.status == approved and executed_event appended.

GOV-T2 — Immutable field enforcement

Attempt to mutate node.registration.registered_by via API; expect ImmutableFieldError and no change.

GOV-T3 — SuperAdmin override & post-hoc review

Call superadmin/override with required signatures; assert EMERGENCY_OVERRIDE event created, replay halted for affected snapshot, and EMERGENCY_REVIEW event pending.

GOV-T4 — Signature verification

Append governance event without signature; system should reject the event creation API call.

GOV-T5 — Quarantine manual-only

Simulate repeated failures; ensure no auto-quarantine. Create quarantine ActionRequest and require council approval to succeed.

GOV-T6 — Governance policy change through PR only

Attempt to change router weights via direct API → rejected. Then create ActionRequest via propose and approve via council → accepted and new snapshot version created.

All governance tests assert canonical serialization and signature presence; use seeded actors and test keys.