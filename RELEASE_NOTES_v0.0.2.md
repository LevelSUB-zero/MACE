# MACE Stage-0 v0.0.2 Release Notes

**Release Date:** 2025-11-30
**Status:** Stage-0 Complete (Ready for Freeze)

## Overview
This release marks the completion of the MACE Stage-0 specification. The system is now a fully deterministic, replayable, and secure cognitive architecture kernel. All 86 validation tests passed.

## Key Features

### 1. Deterministic Replay Engine (Sandbox Mode)
- **Feature**: Replay now executes in a strict "Sandbox Mode" using an ephemeral in-memory Semantic Store (`ReplaySEMStore`).
- **Guarantee**: Replay is mathematically guaranteed to be side-effect free. It will never write to the live SQLite database or journal.
- **Verification**: `test_replay_side_effects.py` confirms database checksums remain identical before and after replay.

### 2. Evidence Management & Artifacts
- **Feature**: Evidence payloads exceeding 16KB (`MAX_EVIDENCE_SIZE`) are automatically redacted from the JSON log.
- **Storage**: Large payloads are offloaded to the `artifacts/` directory as SHA256-named binary files.
- **Provenance**: Logs contain a `provenance` record with the `artifact_url` (e.g., `artifacts://<sha256>.bin`).

### 3. Log Security (HMAC Signing)
- **Feature**: Every `ReflectiveLogEntry` is now cryptographically signed using HMAC-SHA256.
- **Integrity**: The `verify_log_entry` function ensures logs have not been tampered with after creation.

### 4. Deep Verification
- **Feature**: The Replay Engine now performs deep structural equality checks on all log fields, including `reasoning_trace`, `router_decision`, and `memory_reads`.
- **Debugging**: Mismatches produce granular diffs in the error output (e.g., `AGENT_OUTPUT_MISMATCH: Expected "foo", got "bar"`).

### 5. Robustness & Ops
- **Concurrency**: Verified safe concurrent writes to Semantic Memory.
- **Cleanup**: Added test fixtures for reliable database cleanup.
- **Telemetry**: Implemented operational metrics counters.

## Bug Fixes
- **Schema**: Fixed corrupted `ReflectiveLogEntry` and `SelfModel` definitions in `ra9_json_schemas.json`.
- **Replay**: Fixed `MEMORY_READS_MISMATCH` by explicitly recording cache misses (`exists=False`) during replay.
- **Router**: Aligned `qcp.py` regex with `math_agent.py` to strictly enforce integer-only math (no decimals).
- **Tests**: Fixed various logic errors in `test_replay.py`, `test_fuzz.py`, and `test_security.py`.

## Usage
### Running Tests
```bash
$env:PYTHONPATH='src'; pytest tests/v02_validation/ tests/health_check/
```

### Replay Example
```python
from mace.core import replay
from mace.core import reflective_log

# Load a log entry
entry = ... 

# Verify signature
if reflective_log.verify_log_entry(entry, "secret_key"):
    # Replay
    result = replay.replay_log(entry)
    if result["success"]:
        print("Replay successful!")
    else:
        print(f"Replay failed: {result['error']}")
```
