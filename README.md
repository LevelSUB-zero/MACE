# MACE (Massive Autonomous Cognitive Entity) - Stage 0

**Version:** v0.0.2  
**Status:** Stage-0 Complete (Stable)

## Overview
MACE is a deterministic, replayable, and secure cognitive architecture designed for high-fidelity agentic operations. Stage-0 focuses on the kernel: the fundamental loops, memory systems, and verification engines required to build safe AI agents.

## Core Features

### 🧠 Deterministic Kernel
- **Replay Engine**: Mathematically guaranteed side-effect-free replay of any session using a strict "Sandbox Mode".
- **Reflective Logs**: Immutable, HMAC-signed logs (`reflective_log.jsonl`) that capture every percept, decision, and memory state.
- **Deep Verification**: Granular structural equality checks ensure that replayed execution matches original execution bit-for-bit.

### 💾 Semantic Memory (SEM)
- **Canonical Keys**: Enforced `category/subcategory/namespace/name` schema.
- **Journaling**: Append-only write journal (`sem_write_journal.jsonl`) for full state reconstruction.
- **Artifact Offloading**: Large evidence payloads (>16KB) are automatically redacted and stored as content-addressed artifacts (`artifacts/`).

### 🛡️ Security & Governance
- **PII Blocking**: Regex-based blocking of sensitive data (CC, SSN) at the storage layer.
- **Policy Enforcement**: Governance module (`amendment.py`) can block specific keys or patterns.
- **Tamper Evidence**: All logs are cryptographically signed.

## Installation

```bash
# Clone the repository
git clone https://github.com/LevelSUB-zero/MACE.git
cd MACE

# Install dependencies (Standard Python 3.12+)
pip install -r requirements.txt
```

## Usage

### Running the Executor
```python
from mace.runtime import executor

# Execute a query
output, log_entry = executor.execute("What is 2 + 2?")
print(output["text"]) 
# Output: "The result of 2 + 2 is 4"
```

### Replaying a Log
```python
from mace.core import replay

# Replay ensures the exact same execution path is followed
result = replay.replay_log(log_entry)
if result["success"]:
    print("Replay verified!")
else:
    print(f"Divergence detected: {result['error']}")
```

## Testing
Run the comprehensive validation suite:
```bash
$env:PYTHONPATH='src'; pytest tests/v02_validation/ tests/health_check/
```

## Directory Structure
- `src/mace/core`: Kernel components (Deterministic PRNG, Replay, Structures).
- `src/mace/memory`: Semantic Memory & Storage Backends.
- `src/mace/runtime`: Executor & Orchestration.
- `src/mace/agents`: Agent implementations (Math, Profile, Knowledge).
- `tests/`: Validation and Health Check suites.
- `schemas/`: JSON Schemas for all system objects.

## License
Proprietary / Closed Source (LevelSUB-zero).
