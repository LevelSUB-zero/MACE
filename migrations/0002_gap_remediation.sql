-- Stage-1 Gap Remediation Migration
-- Adds brainstate_snapshots table and graph snapshot storage

-- BrainState snapshot storage
CREATE TABLE IF NOT EXISTS brainstate_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  job_seed TEXT NOT NULL,
  brainstate_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  tick_count INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_brainstate_job_seed ON brainstate_snapshots(job_seed);
CREATE INDEX IF NOT EXISTS idx_brainstate_created ON brainstate_snapshots(created_at DESC);

-- Self-representation graph snapshots
CREATE TABLE IF NOT EXISTS selfrep_graph_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  graph_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);
