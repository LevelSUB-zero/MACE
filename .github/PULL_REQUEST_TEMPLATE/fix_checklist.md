## Fix Checklist PR

### Summary
- Short description of the problem and the fix.

### Files changed
- list of high-level files modified.

### Tests added/updated
- [ ] test_replay_no_side_effects
- [ ] test_evidence_size_boundary
- [ ] test_reflective_log_signature_verify
- [ ] test_deep_replay_diff
- [ ] test_concurrent_sem_writes_smoke

### Manual checks performed
- [ ] Ran full test suite locally: `pytest -q`
- [ ] Verified replay produces no DB side effects (sha256 check)
- [ ] Verified evidence `raw_payload=null` for >16KB and artifact created
- [ ] Verified log signature verification passes
- [ ] Verified CI `spec/validate` job passes (jsonschema)

### Rollout / migration notes
- If changing schema, include migration plan and sample migration script.
- If enabling artifact storage, document how artifacts are retained and access-controlled.

### Reviewer checklist
- [ ] Confirm deterministic_id/timestamp behavior unchanged
- [ ] Confirm no direct writes in replay mode
- [ ] Confirm evidence artifact URL structure and access policy
- [ ] Confirm new tests exist and pass in CI
