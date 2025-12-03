# MACE Architecture

System architecture and design documentation for Stage-1.

## Overview

MACE (Memory-Augmented Cognitive Engine) is a **deterministic cognitive execution engine** designed for reproducible, auditable AI agent interactions.

## Design Principles

1. **Determinism**: Every execution is reproducible given a seed
2. **Auditability**: Complete audit trail with signed logs
3. **Persistence**: State survives across restarts
4. **Security**: Token-based auth with kill-switch
5. **Modularity**: Clear separation of concerns

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MACE Stage-1                              │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌───────▼───────┐
│   Executor     │  │   Governance    │  │    Memory     │
│   (Runtime)    │  │   (Admin)       │  │   (Layers)    │
└───────┬────────┘  └────────┬────────┘  └───────┬───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Persistence   │
                    │   (Database)    │
                    └─────────────────┘
```

## Core Components

### 1. Executor (`src/mace/runtime/executor.py`)

**Purpose**: Orchestrates the full execution cycle

**Flow**:
1. **Kill-Switch Check**: Verify system not halted
2. **Seed Chaining**: Initialize deterministic seed
3. **Percept Creation**: Structure input
4. **BrainState Load**: Load or create state
5. **Router**: Select agent deterministically
6. **Agent Execution**: Run selected agent
7. **Council**: Approve output
8. **Reflective Log**: Sign and persist
9. **BrainState Save**: Persist updated state

**Key Features**:
- Deterministic execution path
- State persistence across runs
- Signed reflective logs
- Kill-switch enforcement

### 2. Router (`src/mace/router/stage1_router.py`)

**Purpose**: Deterministic agent selection

**Algorithm**:
```python
1. Score agents based on:
   - Capability match with percept
   - Intent alignment
   - BrainState context

2. Deterministic tie-breaking:
   - Sort by score (descending)
   - Then by agent_id (ascending)

3. Return top-scoring agent
```

**Output**: `ExtendedRouterDecision` with selected agent and metadata

### 3. BrainState (`src/mace/brainstate/`)

**Purpose**: Persistent execution state

**Components**:
- **Goals**: Stack of current objectives
- **Working Memory**: Short-term storage with TTL
- **Attention Map**: Focus weights
- **Tick Counter**: Time tracking

**Operations**:
- `create_snapshot()`: Initialize state
- `tick()`: Advance time, decay attention
- `add_wm_item()`: Add to working memory with FIFO eviction
- `push_goal()` / `pop_goal()`: Manage objectives

**Persistence**: Saved to `brainstate_snapshots` table

### 4. Memory Hierarchy

```
Working Memory (WM)
    ↓ (TTL expires or explicit promotion)
Consolidated Working Memory (CWM)
    ↓ (consolidation process)
Episodic Memory
    ↓ (semantic extraction)
Semantic Memory
```

**Working Memory** (`src/mace/memory/wm.py`):
- Capacity: 7 items (configurable)
- TTL: 10 ticks
- FIFO eviction

**Episodic Memory** (`src/mace/memory/episodic.py`):
- Long-term event storage
- Deterministic IDs
- Provenance tracking

**Semantic Memory** (`src/mace/memory/semantic.py`):
- Knowledge graph
- PII filtering
- Size limits enforced

### 5. APT Engine (`src/mace/apt/engine.py`)

**Purpose**: Append-only audit trail

**Features**:
- Monotonic sequence numbers
- Event replay capability
- Deterministic event IDs

**Event Types**:
- `SNAPSHOT_CREATED`
- `GOAL_PUSHED`
- `MEMORY_ADDED`
- `STATE_UPDATED`

### 6. Reflective Log (`src/mace/reflective/writer.py`)

**Purpose**: Signed execution logs

**Structure**:
```json
{
  "log_id": "deterministic_hash",
  "percept": {...},
  "router_decision": {...},
  "brainstate_before": {...},
  "brainstate_after": {...},
  "agent_outputs": [...],
  "final_output": {...},
  "signature": "HMAC-SHA256"
}
```

**Signature**: HMAC-SHA256 over canonical JSON

### 7. Governance (`src/mace/governance/`)

**Admin Tokens** (`admin.py`):
- Secure generation with `secrets`
- TTL tracking
- Revocation support

**Kill-Switch** (`killswitch.py`):
- File-based flag: `mace_killswitch.flag`
- Halts all executions
- Reason and activator tracking

**Rehydration** (`src/mace/core/rehydrate.py`):
- Rebuilds BrainState from episodic memory
- Extracts goals and WM from episodes

### 8. Self-Representation (`src/mace/self_representation/core.py`)

**Purpose**: Module registry and dependency graph

**Features**:
- Module registration with schema validation
- Version tracking
- Dependency edges
- Graph snapshots

**Operations**:
- `register_module()`: Add/update module
- `register_edge()`: Define relationships
- `graph_snapshot()`: Capture full graph
- `decommission_module()`: Mark offline

## Data Flow

### Execution Flow

```
User Input
    ↓
┌─────────────────┐
│   Executor      │
└────────┬────────┘
         │
    ┌────▼────┐
    │  Router │
    └────┬────┘
         │
    ┌────▼────────┐
    │  Agent      │
    │  Execution  │
    └────┬────────┘
         │
    ┌────▼────┐
    │ Council │
    └────┬────┘
         │
    ┌────▼────────────┐
    │ Reflective Log  │
    │   (Signed)      │
    └────┬────────────┘
         │
    ┌────▼─────────────┐
    │  Save BrainState │
    └──────────────────┘
```

### Memory Flow

```
Agent Output
    ↓
Working Memory (7 items, 10 ticks TTL)
    ↓ (on expiration)
Consolidated WM (20 items, ephemeral)
    ↓ (consolidation)
Episodic Memory (persistent)
    ↓ (semantic extraction)
Semantic Memory (knowledge graph)
```

## Database Schema

### Core Tables

**brainstate_snapshots**:
- `snapshot_id` (PK): Deterministic hash
- `job_seed`: Execution seed
- `brainstate_json`: Full state
- `created_at`: Timestamp
- `tick_count`: State age

**reflective_logs**:
- `log_id` (PK): Deterministic hash
- `log_type`: "execution"
- `log_json`: Full log entry
- `signature`: HMAC-SHA256
- `created_at`: Timestamp

**admin_tokens**:
- `token_id` (PK): Deterministic ID
- `token_hash`: Secure hash
- `purpose`: Use case
- `created_at`, `expires_at`
- `revoked`: Boolean

### Supporting Tables
- `apt_events`: Audit trail
- `episodic`: Long-term memory
- `self_representation_nodes`: Module registry
- `self_representation_edges`: Dependencies
- `selfrep_graph_snapshots`: Graph captures

## Determinism Implementation

### Seed Chain

```
User Seed
    ↓
SHA256(current_seed + percept + intent)
    ↓
Next Seed
    ↓
All operations use PRNG seeded from this
```

### Deterministic Components
- **IDs**: `SHA256(type + payload + counter)`
- **Timestamps**: Monotonic counter-based
- **Router**: Stable sorting with tie-breaking
- **Random**: Seeded PRNG, no system randomness

### Canonicalization

```python
{
  "b": 2,
  "a": 1
}
↓ (canonical_json_serialize)
'{"a":1,"b":2}'  # Sorted keys, no whitespace
```

## Security Model

### Signature Chain

```
Reflective Log Entry
    ↓
Canonical JSON Serialize
    ↓
HMAC-SHA256(payload, signing_key)
    ↓
Store signature with log
```

### Verification

```
1. Load log from DB
2. Extract signature
3. Recompute HMAC
4. Compare signatures
```

### Kill-Switch

```
Executor Entry
    ↓
Check mace_killswitch.flag exists?
    ↓ YES
Raise RuntimeError("KILL_SWITCH_ACTIVE")
    ↓ NO
Continue execution
```

## Configuration Management

### Config Files

**limits.yaml**:
```yaml
wm_capacity: 7
wm_ttl_ticks: 10
attention_decay: 0.9
default_token_budget: 1000
```

**keys.yaml**:
```yaml
signing_keys:
  default: secret-key
```

**Loader**: `src/mace/config/config_loader.py`
- YAML parsing
- Caching
- Getters for specific values

## Deployment Architecture

### Development
```
SQLite DB (single file)
    ↓
Local executor
    ↓
File-based logs
```

### Staging
```
PostgreSQL (staging server)
    ↓
Load-balanced executors
    ↓
Centralized logging
```

### Production
```
PostgreSQL (HA cluster)
    ↓
Multi-region executors
    ↓
Monitoring + Alerts
    ↓
Archive to cold storage
```

## Performance Characteristics

### Latency
- **p50**: 88ms
- **p95**: 118ms
- **p99**: 249ms

### Bottlenecks
1. Database I/O (BrainState load/save)
2. Signature computation (HMAC)
3. Canonical JSON serialization

### Optimizations
- Index on `job_seed`, `created_at`
- Connection pooling (Stage-2)
- Async I/O (Stage-2)

## Extension Points

### Custom Agents
```python
def my_custom_agent(percept, brainstate):
    return {
        "agent_id": "custom",
        "text": "My response",
        "confidence": 0.95
    }
```

### Custom Memory Layers
```python
class MyMemoryLayer:
    def add_item(self, item): ...
    def get_items(self, query): ...
```

### Custom Validators
```python
def my_validator(payload):
    # Custom schema validation
    return is_valid, errors
```

## Stage-2 Preview

Planned enhancements:
- **Vault Integration**: Secure key management
- **Encryption**: Database encryption at rest
- **ML Router**: Embedding-based agent selection
- **Async I/O**: Non-blocking database operations
- **Connection Pooling**: Reuse DB connections
- **Prometheus**: Metrics exporters
- **Grafana**: Visualization dashboards

---

**For implementation details, see source code and inline documentation.**
