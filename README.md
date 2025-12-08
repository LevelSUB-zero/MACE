# MACE (Meta Aware Cognitive Engine)

**Version**: 1.0.0 (Stage-1)  
**Status**: Production Ready ✅

A deterministic cognitive execution engine with 100% replay fidelity, comprehensive validation tooling, and production-ready operational infrastructure.

## ✨ Features

- 🎯 **100% Deterministic Execution** - Guaranteed replay fidelity
- 🧠 **Self-Representation** - Module registry with dependency graphs
- 💾 **Persistent BrainState** - Stateful execution across restarts
- 📜 **Performance Timeline** - Append-only APT event logging (Performance Event Timeline)
- 🔐 **Security** - Admin tokens, kill-switch, HMAC signatures
- ⚡ **High Performance** - p95 latency 118ms
- 🛡️ **Fault Tolerant** - Graceful error handling and fallbacks

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/Mace.git
cd Mace

# Install dependencies
pip install -r requirements.txt

# Set up database
python migrations/migrate_template.py --db mace_stage1.db --sql migrations/0001_create_stage1_tables.sql
python migrations/migrate_template.py --db mace_stage1.db --sql migrations/0002_gap_remediation.sql
```

### Basic Usage

```python
from mace.runtime import executor

# Execute a deterministic task
output, log = executor.execute(
    "Calculate the sum of 2 and 2",
    intent="math",
    seed="my_deterministic_seed"
)

print(output["text"])  # Deterministic result
```

### Verification

```bash
# Run test suite
pytest tests/stage1/ -v

# Verify replay fidelity
python tools/run_replay_benchmark.py --seeds 1..100

# Security validation
python tools/security_validation.py --db mace_stage1.db

# Performance baseline
python tools/benchmark_performance.py --requests 100
```

## 📊 Validation Results

| Component | Tests | Status |
|-----------|-------|--------|
| Core Tests | 28/28 | ✅ |
| Replay Fidelity | 100% | ✅ |
| Security | 4/4 | ✅ |
| Performance (p95) | 118ms | ✅ |
| Fault Injection | 4/4 | ✅ |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│           Executor (Stage-1)                │
├─────────────────────────────────────────────┤
│  1. Router (Deterministic Agent Selection)  │
│  2. BrainState (Persistent State)           │
│  3. Agent Execution                         │
│  4. Council (Approval)                      │
│  5. Reflective Log (Signed)                 │
└─────────────────────────────────────────────┘
         ↓                            ↓
┌──────────────────┐        ┌──────────────────┐
│  Memory Layers   │        │   APT Engine     │
│  - Working       │        │  (Audit Trail)   │
│  - Consolidated  │        └──────────────────┘
│  - Episodic      │
│  - Semantic      │
└──────────────────┘
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design.

## 📚 Documentation

- **[Usage Guide](docs/USAGE.md)** - Complete usage examples
- **[Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[API Reference](docs/API_REFERENCE.md)** - Function and class documentation
- **[Deployment](ops/runbooks/deployment.md)** - Production deployment guide
- **[Troubleshooting](ops/runbooks/troubleshooting.md)** - Common issues and solutions

## 🔧 Tools

### Validation Tools
- `run_replay_benchmark.py` - Test replay fidelity at scale
- `security_validation.py` - Security and auth validation
- `benchmark_performance.py` - Performance metrics
- `test_fault_injection.py` - Error handling tests

### Operations Tools
- `archive_old_files.sh` - Log cleanup automation
- `preview_cleanup.py` - Safe cleanup preview
- `verify_signatures.py` - Signature verification

## 🔐 Security

- **Admin Tokens**: Secure generation with TTL and revocation
- **Kill-Switch**: Emergency halt capability
- **Signed Logs**: HMAC-SHA256 for integrity
- **Deterministic Replay**: Prevents tampering

See [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) for complete security posture.

## 📈 Performance

```
Latency (50 requests):
  p50: 88ms
  p95: 118ms
  p99: 249ms

Throughput: 100% success rate
Error rate: 0%
```

## 🧪 Testing

```bash
# Full test suite
pytest tests/stage1/ -v

# Specific modules
pytest tests/stage1/test_executor.py -v
pytest tests/stage1/test_replay.py -v

# With coverage
pytest tests/stage1/ --cov=src/mace --cov-report=html
```

## 🛠️ Development

### Setup Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

### Run Linting

```bash
black src/ tests/ --line-length=100
isort src/ tests/ --profile=black
flake8 src/ tests/ --max-line-length=100
```

## 📦 Release History

- **v1.0.0** (2025-12-03) - Stage-1 production release
- **v0.0.2** (2025-11-XX) - Stage-0 with deterministic primitives
- **v0.0.1** (2025-XX-XX) - Initial prototype

See [RELEASE_NOTES_v1.0.0.md](RELEASE_NOTES_v1.0.0.md) for detailed changelog.

## 🗺️ Roadmap

### Stage-2 (Planned)
- Vault integration for secrets management
- Database encryption at rest
- Advanced monitoring (Prometheus/Grafana)
- ML-based router scoring
- Performance optimizations

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

[Add your license here]

## 🔗 Links

- [Documentation](docs/)
- [GitHub Issues](https://github.com/yourusername/Mace/issues)
- [Release Notes](RELEASE_NOTES_v1.0.0.md)

---

**Built with precision for deterministic execution** 🎯
