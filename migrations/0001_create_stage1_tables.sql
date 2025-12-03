-- Stage-1 Tables DDL

CREATE TABLE IF NOT EXISTS self_representation_nodes (
  module_id TEXT PRIMARY KEY,
  node_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  version INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS self_representation_edges (
  edge_id TEXT PRIMARY KEY,
  edge_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS apt_events (
  event_id TEXT PRIMARY KEY,
  node_id TEXT NOT NULL,
  event_json JSONB NOT NULL,
  event_sequence_idx BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS reflective_logs (
  log_id TEXT PRIMARY KEY,
  log_json JSONB NOT NULL,
  immutable_subpayload JSONB NOT NULL,
  signature TEXT,
  signature_key_id TEXT,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS episodic (
  episodic_id TEXT PRIMARY KEY,
  job_seed TEXT,
  summary TEXT,
  payload JSONB,
  created_seeded_ts TEXT,
  provenance JSONB
);

CREATE TABLE IF NOT EXISTS admin_tokens (
  token_id TEXT PRIMARY KEY,
  token_hash TEXT NOT NULL,
  purpose TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  revoked BOOLEAN DEFAULT FALSE
);
