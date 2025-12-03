# MACE Stage-1 Troubleshooting Guide

## Common Issues

### Tests Failing: Import Errors for `migrations` module
**Symptom**: `ImportError: No module named 'mace.migrations'`

**Cause**: The `migrations/` directory is at project root, not in `src/mace/`

**Solution**: Tests should use:
```python
import sys
sys.path.append(os.getcwd())
from migrations import migrate_template
```

---

### Database: `OperationalError: no such table`
**Symptom**: `OperationalError: no such table: reflective_logs`

**Cause**: Database migrations not run

**Solution**:
```bash
python migrations/migrate_template.py --db sqlite:///mace_stage1.db --sql migrations/0001_create_stage1_tables.sql
```

---

### Replay Fidelity: Log ID Mismatch
**Symptom**: Replay test fails with `LOG_ID_MISMATCH`

**Cause**: Non-deterministic code (e.g., `datetime.now()`, `uuid.uuid4()`)

**Solution**: Use deterministic equivalents:
- Replace `datetime.now()` → `deterministic.deterministic_timestamp()`
- Replace `uuid.uuid4()` → `deterministic.deterministic_id()`

---

### Admin Tokens: Column Not Found
**Symptom**: `OperationalError: table admin_tokens has no column named purpose`

**Cause**: Database schema outdated

**Solution**: Re-run migrations with updated DDL:
```bash
rm mace_stage1.db  # Delete old DB
python migrations/migrate_template.py --db sqlite:///mace_stage1.db --sql migrations/0001_create_stage1_tables.sql
```

---

### Kill-Switch: Not Activating
**Symptom**: `killswitch.is_active()` returns `False` despite activation

**Cause**: File permissions or working directory issue

**Solution**:
1. Check file exists: `ls mace_killswitch.flag`
2. Verify file content: `cat mace_killswitch.flag`
3. Ensure working directory is project root

---

### Signature Verification Fails
**Symptom**: `tools/verify_signatures.py` reports signature mismatch

**Cause**: Signing key changed or data corruption

**Solution**:
1. Check `keys.yaml` has not changed
2. Verify `immutable_subpayload` matches what was signed
3. Review `signature_key_id` in database

---

### Performance: Tests Running Slowly
**Symptom**: Full test suite takes >30 seconds

**Cause**: Database I/O or test fixtures

**Solution**:
- Use in-memory SQLite: `sqlite:///:memory:`
- Parallelize tests: `pytest -n auto` (requires pytest-xdist)

---

## Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Getting Help
1. Check test output for stack traces
2. Review `walkthrough.md` for implementation details
3. Verify against samples in `samples/` directory
4. Contact development team
