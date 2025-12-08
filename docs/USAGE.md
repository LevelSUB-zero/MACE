# MACE Usage Guide

Complete guide to using the Meta Aware Cognitive Engine (MACE) Stage-1.

## Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Configuration](#configuration)
- [Validation & Testing](#validation--testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites
- Python 3.12+
- SQLite 3 or PostgreSQL 13+

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/Mace.git
cd Mace

# Install dependencies
pip install -r requirements.txt

# Set Python path
export PYTHONPATH=src  # Linux/Mac
$env:PYTHONPATH='src'  # Windows PowerShell

# Run migrations
python migrations/migrate_template.py --db mace_stage1.db --sql migrations/0001_create_stage1_tables.sql
python migrations/migrate_template.py --db mace_stage1.db --sql migrations/0002_gap_remediation.sql
```

## Quick Start

### Basic Execution

```python
from mace.runtime import executor

# Simple execution
output, log_entry = executor.execute(
    "What is 2 + 2?",
    intent="math",
    seed="my_seed_123"
)

print(output["text"])
```

### With Logging

```python
# Enable reflective logging
output, log_entry = executor.execute(
    "Calculate the square root of 16",
    intent="math",
    seed="calc_seed",
    log_enabled=True  # Saves to database
)

# Check log ID for replay
print(f"Log ID: {log_entry['log_id']}")
```

## Core Concepts

### 1. Deterministic Execution
Every execution is fully deterministic given a seed:

```python
from mace.core import deterministic

# Initialize with seed
deterministic.init_seed("test_seed_1")

# All operations are now deterministic
id1 = deterministic.deterministic_id("resource", "data")
id2 = deterministic.deterministic_id("resource", "data")
assert id1 == id2  # Always true
```

### 2. BrainState
Persistent execution state:

```python
from mace.brainstate import brainstate

# Create snapshot
bs = brainstate.create_snapshot("job_seed_123")

# Manage goals
brainstate.push_goal(bs, "solve_problem")
brainstate.pop_goal(bs)

# Working memory
brainstate.add_wm_item(bs, {
    "memory_id": "mem_1",
    "content": "Important fact"
})

# Tick advances time
brainstate.tick(bs)
```

### 3. Memory Layers

```python
from mace.memory import wm, episodic

# Working Memory
wm.add_item(brainstate, {"key": "value"})
items = wm.get_items(brainstate)

# Episodic Memory
episodic.add_episode(
    job_seed="job_1",
    episode_type="decision",
    payload={"action": "calculated", "result": 4}
)
```

### 4. Admin & Governance

```python
from mace.governance import admin, killswitch

# Generate admin token
token, token_id = admin.generate_token("deployment", ttl_hours=24)

# Verify token
result = admin.verify_token(token)
if result["valid"]:
    print("Access granted")

# Emergency kill-switch
killswitch.activate("EMERGENCY", "admin_user")
# All executions will now fail
killswitch.deactivate()
```

## Advanced Features

### Replay & Verification

```python
from mace.replay import replay

# Replay a logged execution
result = replay.replay_log(log_entry)

if result["success"]:
    print("Replay matched!")
else:
    print(f"Mismatch: {result['error']}")
```

### Signature Verification

```python
from mace.core import signing

# Sign data
payload = {"data": "important"}
signature = signing.sign_payload(payload, "key_id")

# Verify signature
is_valid = signing.verify_signature(payload, signature, "key_id")
```

### Self-Representation

```python
from mace.self_representation import core

# Register a module
module = {
    "module_id": "math_solver",
    "version": "1.0.0",
    "capabilities": ["arithmetic", "algebra"],
    "status": "active"
}
core.register_module(module)

# Register relationships
core.register_edge("math_solver", "calculator", "dependency")

# Get graph snapshot
snapshot = core.graph_snapshot()
```

## Configuration

### Config Files

Edit `src/mace/config/limits.yaml`:

```yaml
wm_capacity: 7
wm_ttl_ticks: 10
attention_decay: 0.9
default_token_budget: 1000
max_evidence_size_bytes: 16384
```

Edit `src/mace/config/keys.yaml`:

```yaml
signing_keys:
  default: your-secret-key-here
  production: prod-key-here
```

### Environment Variables

```bash
# Database URL
export MACE_DB_URL="sqlite:///mace_stage1.db"
# or for PostgreSQL
export MACE_DB_URL="postgresql://user:pass@localhost/mace"
```

## Validation & Testing

### Run Test Suite

```bash
# All tests
pytest tests/stage1/ -v

# Specific module
pytest tests/stage1/test_executor.py -v

# With coverage
pytest tests/stage1/ --cov=src/mace --cov-report=html
```

### Replay Benchmark

```bash
# Test 100 executions
python tools/run_replay_benchmark.py --seeds 1..100 --out results.jsonl

# Analyze results
python tools/analyze_replay_results.py results.jsonl
```

### Security Validation

```bash
python tools/security_validation.py --db mace_stage1.db
```

### Performance Benchmark

```bash
# Measure latency
python tools/benchmark_performance.py --requests 100 --output perf.json

# View results
cat perf.json
```

### Fault Injection

```bash
python tools/test_fault_injection.py --db mace_stage1.db
```

## Deployment

### Development

```bash
# Use SQLite
python migrations/migrate_template.py --db dev.db --sql migrations/0001_create_stage1_tables.sql
python migrations/migrate_template.py --db dev.db --sql migrations/0002_gap_remediation.sql

export MACE_DB_URL="sqlite:///dev.db"
```

### Staging

```bash
# Use PostgreSQL
export MACE_DB_URL="postgresql://user:pass@staging-db/mace"

python migrations/migrate_template.py --db "$MACE_DB_URL" --sql migrations/0001_create_stage1_tables.sql
python migrations/migrate_template.py --db "$MACE_DB_URL" --sql migrations/0002_gap_remediation.sql

# Verify
python tools/run_replay_benchmark.py --seeds 1..20
python tools/security_validation.py
```

### Production

See [ops/runbooks/deployment.md](../ops/runbooks/deployment.md) for complete guide.

```bash
# 1. Backup existing data
bash tools/pg_backup.sh

# 2. Run migrations
python migrations/migrate_template.py --db "$PROD_DB_URL" --sql migrations/0002_gap_remediation.sql

# 3. Verify
pytest tests/stage1/
python tools/security_validation.py

# 4. Deploy with kill-switch ready
# Kill-switch file: mace_killswitch.flag
```

## Troubleshooting

### Common Issues

#### "No such table: brainstate_snapshots"

**Solution**: Run migration 0002
```bash
python migrations/migrate_template.py --db mace_stage1.db --sql migrations/0002_gap_remediation.sql
```

#### "Module 'mace.x' has no attribute 'y'"

**Solution**: Set PYTHONPATH
```bash
export PYTHONPATH=src  # Linux/Mac
$env:PYTHONPATH='src'  # Windows
```

#### Replay Mismatch

**Solution**: Check deterministic seed initialization
```python
# Always initialize seed before execution
deterministic.init_seed("your_seed")
```

#### Performance Issues

**Solution**: Enable indexes
```sql
CREATE INDEX IF NOT EXISTS idx_brainstate_job_seed ON brainstate_snapshots(job_seed);
CREATE INDEX IF NOT EXISTS idx_episodic_job ON episodic(job_seed);
```

See [ops/runbooks/troubleshooting.md](../ops/runbooks/troubleshooting.md) for more.

## Best Practices

### 1. Always Use Seeds

```python
# Good
executor.execute("query", seed="unique_seed_123")

# Bad - non-deterministic
executor.execute("query")
```

### 2. Enable Logging in Production

```python
# Production
executor.execute("query", seed="seed", log_enabled=True)
```

### 3. Verify Replay Fidelity

```python
from mace.replay import replay

# After important executions
result = replay.replay_log(log_entry)
assert result["success"], "Replay must match!"
```

### 4. Use Kill-Switch for Emergencies

```python
# In emergency
from mace.governance import killswitch
killswitch.activate("DATA_ISSUE", "ops_team")

# Resume after fix
killswitch.deactivate()
```

### 5. Regular Cleanup

```bash
# Preview old files
python tools/preview_cleanup.py --days 90

# Archive
bash tools/archive_old_files.sh
```

## Examples

### Example 1: Math Calculation

```python
from mace.runtime import executor

output, log = executor.execute(
    "Calculate 15% of 200",
    intent="math",
    seed="calc_001",
    log_enabled=True
)

print(f"Result: {output['text']}")
print(f"Log ID: {log['log_id']}")
```

### Example 2: State Management

```python
from mace.brainstate import brainstate, persistence

# Create state
bs = brainstate.create_snapshot("session_123")
brainstate.push_goal(bs, "complete_task")

# Save state
persistence.save_snapshot(bs)

# Later... load state
loaded_bs = persistence.load_latest_snapshot("session_123")
assert loaded_bs["goals"] == ["complete_task"]
```

### Example 3: Admin Operations

```python
from mace.governance import admin

# Create deployment token
token, token_id = admin.generate_token(
    purpose="api_access",
    ttl_hours=24,
    created_by="admin"
)

# Later, verify
result = admin.verify_token(token)
if result["valid"]:
    # Proceed with operation
    pass
else:
    print(f"Invalid: {result['reason']}")
```

## Next Steps

- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Check [API_REFERENCE.md](API_REFERENCE.md) for complete API docs
- See [../ops/runbooks/](../ops/runbooks/) for operational guides
- Join discussions on GitHub Issues

---

**Need help?** Open an issue on GitHub or check the troubleshooting guide.
