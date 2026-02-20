Replay Constraints — MACE (Stage-1 Final)

One-line purpose: Ensure every run that claims “replayable” can be bit-for-bit reproduced (decisions, logs, IDs, and outputs) from snapshots + ordered events + job_seed, with deterministic protections, tamper detection, and governed emergency paths.

1 — Core principles (non-negotiable)

Determinism first: Every decision-relevant value used during a job must be derivable from: job_seed + job input + snapshots referenced in the job’s ReflectiveLog + ordered append-only event stream.

Snapshot-anchored runs: Every job run must declare which snapshots it uses (SelfRepresentation, BrainState, RouterConfig, PrivacyPolicy, Governance). Replay must load exactly those snapshots.

Append-only provenance: All events that influenced a decision are stored in append-only logs (ReflectiveLog, apt_event, episodic writes, governance events). Replay replays the same ordered stream.

Signature & integrity: Snapshots and logs are HMAC-signed. Replay verifies signatures; any mismatch causes INTEGRITY_FAILURE and halts replay.

No live telemetry in decision path: Live metrics (CPU, RAM, ephemeral latencies) may be logged for ops but never used during a replayed decision.

Deterministic RNG: Any randomness must be seeded from job_seed and recorded; RNG draws are reproducible.

Conservative failover: If required data for replay is missing/invalid, replay must fail CLOSED (halt) and require human/council action — never attempt to “guess”.

2 — Replay modes

Audit Replay (read-only): Reconstruct entire decision trace for investigation; verifies signatures, reproduces outputs, produces audit diff. Allowed to run on archived snapshots.

Replay & Reexecute (test): Reconstruct trace and optionally re-run agents/tools in sandbox (must use mocked LLMs or saved agent outputs to avoid nondeterminism). Useful for regression tests.

Production Replay (strict): Intended only for disaster recovery/forensics; uses exact snapshots and event stream; refuses any live external calls (LLM/tool) unless those outputs were persisted in the original trace.

Each mode is flagged in replay_request and recorded.

3 — Required pieces for a successful replay

job_id and job_seed (seeded RNG base).

ReflectiveLog trace for the job (full iteration_trace).

Snapshot IDs referenced in ReflectiveLog:

selfrep_snapshot_id

brainstate_snapshot_id

router_snapshot_id

privacy_snapshot_id

governance_snapshot_id

Append-only event streams referenced by ReflectiveLog (APT events, ActionRequests, episodic writes, council votes).

Stored agent outputs for any external calls (LLM outputs, tool results) if original run persisted them. If not persisted, production replay must not call live external services — require sandboxed mocks.

Server key for signature verification (ops only).

Canonical JSON serializer + numeric formatting rules used at original runtime.

All of the above must be present; otherwise reply with deterministic error codes (see §8).

4 — Canonicalization & numeric rules (must be enforced)

Canonical JSON serializer: sort keys, use UTF-8, no extra whitespace, deterministic float formatting with NUMERIC_PRECISION = 9 decimals, NUMERIC_EPSILON = 1e-9.

Deterministic ordering for arrays used in decisions: sort by defined deterministic key (e.g., (apt desc, node_id asc)) before serialization into snapshot.

Event ordering: order by event_sequence_index (deterministic, derived from seed + monotonic counter). Use this order for replay.

Include canonical serializer code in repo and use in CI (tests rely on exact string equality).

5 — Deterministic event & id derivation (exact)

Use seeded deterministic functions:

event_id = sha256(job_seed + ":" + sequence_index + ":" + event_type)

snapshot_id = sha256(config_hash + ":" + schema_version + ":" + seed_namespace)

wm_id = sha256(job_seed + ":" + wm_counter)

episodic_id = sha256(job_seed + ":" + episodic_counter)

Record the generator function and seed in snapshot metadata so replay can verify id provenance.

6 — Replay algorithm (pseudocode — implement exactly)
def replay_job(job_id, mode="audit"):
    # 1. load reflective log entry for job_id
    refl = load_reflective_log(job_id)
    # 2. verify required snapshot ids present
    required_snapshots = [refl.selfrep_snapshot_id, refl.brainstate_snapshot_id,
                          refl.router_snapshot_id, refl.privacy_snapshot_id, refl.governance_snapshot_id]
    if any_missing(required_snapshots):
        raise ReplayError("MISSING_SNAPSHOT", details=which_missing)

    # 3. load and verify snapshot signatures
    snapshots = [load_snapshot(sid) for sid in required_snapshots]
    for s in snapshots:
        if not verify_signature(s):
            append_event("INTEGRITY_FAILURE", job_id=job_id, snapshot_id=s.id)
            raise ReplayError("INTEGRITY_FAILURE", snapshot_id=s.id)

    # 4. load ordered event streams referenced in refl (apt_events, actionrequests, episodics)
    events = load_ordered_events(refl.event_refs)  # ordered by event_sequence_index
    # 5. seed deterministic RNG
    rng = DeterministicRNG(refl.job_seed)

    # 6. optional: load persisted agent outputs (if production replay requires exact outputs)
    persisted_outputs = load_persisted_agent_outputs(job_id)

    # 7. re-run deterministic reducers:
    #    - materialize SelfRepresentation via reducer(events, snapshots.selfrep_start)
    #    - materialize BrainState via brainstate_replay(refl.brainstate_snapshot, events, rng)
    materialized_selfrep = reducer_replay(snapshots.selfrep, events)
    materialized_brainstate = brainstate_replay(snapshots.brainstate, events, rng)

    # 8. step through iteration_trace: for each iteration, re-evaluate router.decide using snapshots + materialized states
    for it in refl.iteration_trace:
        router_out = router_replay(it.router_input_snapshot, materialized_selfrep, materialized_brainstate, rng)
        compare(router_out, it.router_output)  # must match bit-for-bit, else record divergence

        # if production mode and agent outputs were persisted, compare them; else refuse to call live agents
        if mode == "production":
            if it.agent_output_id in persisted_outputs:
                assert persisted_outputs[it.agent_output_id] == it.agent_output
            else:
                raise ReplayError("MISSING_PERSISTED_AGENT_OUTPUT", it_id=it.iteration_id)

    # 9. compute final result and compare to stored final_answer
    if computed_final_answer != refl.final_answer:
        record_divergence(job_id, computed_final_answer, refl.final_answer)
        raise ReplayError("RESULT_MISMATCH")

    return replay_success_report()


Implementers: follow this algorithm exactly and log every verification step in a replay audit result (append-only).

7 — Handling nondeterminism & missing persisted outputs

If an external output was not persisted (LLM result not stored), production replay MUST HALT and return MISSING_PERSISTED_AGENT_OUTPUT. Do not call live LLMs in production replay.

Audit replay mode may allow calling live services only in a sandbox mode with mocks and must note difference. Always mark result as “non-authoritative” if live calls were used.

Divergence detection: if any intermediate computed object differs from recorded one (router output, agent output, brainstate tick), append REPLAY_DIVERGENCE event with deterministic diff and stop unless operator explicitly requests “force-continue” (requires Admin + Council log). Force-continue remains non-authoritative.

8 — Deterministic error codes (always exact strings)

MISSING_SNAPSHOT

INTEGRITY_FAILURE

MISSING_PERSISTED_AGENT_OUTPUT

RESULT_MISMATCH

REPLAY_DIVERGENCE

FORCE_CONTINUE_REQUIRED

Use these exact strings in tests/alerts.

9 — Preservation rules (what to persist during original run)

To enable production replay later, the original run MUST persist:

All snapshots used (selfrep, brainstate, router_config, privacy, governance) with signatures.

Full ReflectiveLog with iteration_trace and router_decision objects.

All append-only events referenced (APT events, ActionRequests, episodic writes, council votes).

Agent outputs that came from external, non-deterministic systems (LLM outputs, external tool responses) — these MUST be stored if you want strict production replay. If these are not stored, record that job as non-replayable in production mode.

Implementer: add an enforcement check at job end that marks job as REPLAYABLE: true/false based on stored artifacts; save this flag in ReflectiveLog.

10 — Governance & replay

Replay access control: Only Operator/Admin/Auditor roles may run replays; production replay restricted to Admin+Auditor or Council-approved. All replay attempts append REPLAY_REQUEST event with actor_id, mode, and must be signed.

Emergency halts: INTEGRITY_FAILURE or SECURITY_INCIDENT events set FORCE_HALT_REPLAY on affected snapshots until council clears it (append-only FORCE_HALT_CLEAR event).

Replay for legal requests (DSR): DSR flows that require reproducing past interactions must run in audit mode; any unredacted PII available only to Admin with logged access events.

11 — Golden tests (Replay-specific)

All replay tests use seeded data and canonical serializer. Examples:

REPLAY-01 — Full replay equality

Setup: run job with seed=s1, persist agent outputs.

Test: run production replay.

Expectation: replay succeeds; computed final answer exactly equals stored final_answer; no divergence events.

REPLAY-02 — Missing snapshot fails

Remove one snapshot file referenced by ReflectiveLog. Replay → MISSING_SNAPSHOT error.

REPLAY-03 — Signature mismatch

Tamper with snapshot JSON (flip a byte). Replay → INTEGRITY_FAILURE, job halts.

REPLAY-04 — Missing persisted agent output

Remove persisted LLM output for iteration i. Production replay → MISSING_PERSISTED_AGENT_OUTPUT.

REPLAY-05 — Replay divergence detection

Change persisted router output to a wrong value. Replay should detect difference during compare() and record REPLAY_DIVERGENCE.

REPLAY-06 — Force-continue requires governance

On divergence, attempt to FORCE_CONTINUE without admin+ council → request rejected. With signed approval appended in governance events → proceed but mark results non-authoritative.

REPLAY-07 — Non-production sandbox run allowed

Sandbox replay that calls live LLMs with mocks; verify run produces a non-authoritative badge in replay report.

All tests must assert exact error strings and include canonical serialized diffs.

12 — Operational notes & perf

Archive strategy: Persist snapshots & essential artifacts in immutable object store (S3 with object versioning); use content-addressed naming (snapshot_id).

Storage cost: Persisting all agent outputs is expensive; mark which jobs require strict replay (e.g., high-risk or golden runs). Default: persist external outputs for any job that changes SEM or governance.

Replay runtime limits: enforce a max replay time and iteration cap (snapshot constants) to avoid runaway forensic jobs. If exceeded, append REPLAY_TIMEOUT event.

13 — Implementation checklist for Ayushmaan

Implement replay service POST /replay/request that: validates actor, verifies snapshot signatures, loads events, seeds RNG, runs replay_job() as per §6, and appends REPLAY_RESULT event.

Add job.replayable flag enforcement at job end based on persisted artifacts.

Include canonical JSON serializer module and a canonical float formatter. Add to CI checks.

Add replay golden tests REPLAY-01..REPLAY-07 to CI with seeded fixtures.

Add ops dashboard showing missing artifacts for non-replayable jobs.

14 — Final guardrails (short)

Never attempt to reconstruct missing nondeterministic outputs from live calls during a production replay. Halt and require governance.

Always verify signatures before replaying.

Use seeded RNG everywhere; store seed in ReflectiveLog.

Keep replay logs immutable and append-only.