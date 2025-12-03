# MACE Stage-1 Rollback Procedure

## When to Rollback
- Critical bug detected in production
- Data integrity issues
- Performance degradation
- Security incident

## Pre-Rollback Checklist
- [ ] Identify rollback target version
- [ ] Notify stakeholders
- [ ] Backup current database state
- [ ] Activate kill-switch to halt new executions

## Rollback Steps

### 1. Activate Kill-Switch
```python
from mace.governance import killswitch
killswitch.activate("ROLLBACK_IN_PROGRESS", "ops_team")
```

### 2. Backup Current State
```bash
# Backup database
tools/pg_backup.sh

# Archive current reflective logs
python tools/export_selfrep.sh  # Export self-representation state
```

### 3. Revert Code
```bash
# Identify last known good commit
git log --oneline

# Checkout previous version
git checkout <commit-hash>

# Or rollback to previous tag
git checkout <previous-tag>
```

### 4. Database Rollback (if needed)
**Option A: Restore from backup**
```bash
tools/pg_restore.sh <backup-file>
```

**Option B: Manual rollback**
- If only data issues, may not need schema rollback
- Review recent transactions and revert if possible

### 5. Verification
```bash
# Run tests
PYTHONPATH=src pytest tests/stage1/ -v

# Verify signatures
python tools/verify_signatures.py

# Test replay
python tools/replay_verify.py <sample-log-id>
```

### 6. Gradual Re-enable
```python
# Deactivate kill-switch
from mace.governance import killswitch
killswitch.deactivate("ops_team")
```

### 7. Monitor
- Watch for errors in logs
- Verify execution counts normalizing
- Check replay fidelity on new logs

## Post-Rollback
1. **Root Cause Analysis**: Identify what went wrong
2. **Document Incident**: Update incident log
3. **Plan Fix**: Create ticket for proper fix
4. **Test Thoroughly**: Ensure fix addresses root cause before re-deploy

## Emergency Contacts
- On-call engineer: [contact]
- Database admin: [contact]
- Security team: [contact]

## Data Preservation
**CRITICAL**: Never delete data during rollback unless authorized by security team. Always:
1. Backup before any destructive action
2. Archive suspicious data for forensics
3. Document all rollback actions in incident log
