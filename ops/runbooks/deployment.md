# MACE Stage-1 Deployment Guide

## Prerequisites
- Python 3.12+
- PostgreSQL 14+ (production) or SQLite (development)
- Git access to repository

## Environment Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd Mace
git checkout stage1/implement
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
# Core: jsonschema
# Optional: psycopg2 (for Postgres)
```

### 3. Database Setup

#### Development (SQLite)
```bash
# Run migrations
python migrations/migrate_template.py --db sqlite:///mace_stage1.db --sql migrations/0001_create_stage1_tables.sql
```

#### Production (Postgres)
```bash
# Set environment variable
export MACE_DB_URL="postgresql://user:password@localhost:5432/mace_stage1"

# Run migrations
python migrations/migrate_template.py --db "$MACE_DB_URL" --sql migrations/0001_create_stage1_tables.sql
```

### 4. Configuration
```bash
# Create config files (if needed)
cp src/mace/config/keys.yaml.example src/mace/config/keys.yaml
# Edit keys.yaml with your signing keys
```

## Deployment Steps

### Staging Deployment
1. **Deploy to staging environment**
2. **Run smoke tests**: `PYTHONPATH=src pytest tests/stage1/ -v`
3. **Verify database connectivity**
4. **Test execution cycle**: `python -c "from mace.runtime import executor; print(executor.execute('2+2', intent='math'))"`
5. **Check logs**: Verify `reflective_logs` table has signed entries

### Production Deployment
1. **Backup existing database**: `tools/pg_backup.sh`
2. **Deploy code to production servers**
3. **Run migrations**: Use `migrate_template.py` with production DB URL
4. **Verify migrations**: Check all tables exist
5. **Gradual rollout**: Start with 10% traffic
6. **Monitor**: Check for errors, signature verification
7. **Scale up**: Increase to 100% if stable

## Verification

### Post-Deployment Checks
```bash
# 1. Verify all tests pass in prod environment
PYTHONPATH=src pytest tests/stage1/

# 2. Verify schema validation
python tools/jsonschema_validate.py schemas/ra9_schema_bundle.json samples/reflective_sample.json

# 3. Verify signatures
python tools/verify_signatures.py --db "$MACE_DB_URL"

# 4. Test replay fidelity
# (Get a log_id from reflective_logs table)
python tools/replay_verify.py <log_id> --db "$MACE_DB_URL"
```

## Rollback Procedure
See `ops/runbooks/rollback.md`

## Monitoring
- Check `ops/metrics.json` for execution counts
- Monitor database disk usage
- Review `reflective_logs` table for anomalies

## Troubleshooting
See `ops/runbooks/troubleshooting.md`
