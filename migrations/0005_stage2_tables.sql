-- Stage-2 Event Logging Tables
-- Spec: docs/stage2_ideology.md, Phase 2.1

-- Stage-2 Events (append-only)
CREATE TABLE IF NOT EXISTS stage2_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source_module TEXT NOT NULL,
    event_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Index for event type queries
CREATE INDEX IF NOT EXISTS idx_stage2_events_type ON stage2_events(event_type);

-- MEM-SNN Shadow Predictions (never read by live code)
CREATE TABLE IF NOT EXISTS mem_snn_shadow_predictions (
    prediction_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    predicted_truth_score REAL,
    predicted_utility_score REAL,
    predicted_safety_score REAL,
    ranking_position INTEGER,
    confidence_interval REAL,
    created_at TEXT NOT NULL
);

-- MEM-SNN Divergence Log (for training analysis)
CREATE TABLE IF NOT EXISTS mem_snn_divergence_log (
    divergence_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    mem_snn_prediction TEXT NOT NULL,
    council_decision TEXT NOT NULL,
    divergence_reason TEXT,
    created_at TEXT NOT NULL
);

-- Stage-2 Candidates (extends LR-01 structure)
CREATE TABLE IF NOT EXISTS stage2_candidates (
    candidate_id TEXT PRIMARY KEY,
    features_json TEXT NOT NULL,
    proposed_key TEXT NOT NULL,
    value TEXT NOT NULL,
    episodic_ids_json TEXT NOT NULL,
    job_seed TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Stage-2 Council Labels (immutable)
CREATE TABLE IF NOT EXISTS stage2_council_labels (
    label_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    truth_label INTEGER,
    safety_label INTEGER,
    utility_label INTEGER,
    governance_label TEXT NOT NULL,
    has_conflict INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- Stage-2 Amendments (append-only, delayed rewards)
CREATE TABLE IF NOT EXISTS stage2_amendments (
    amendment_id TEXT PRIMARY KEY,
    original_candidate_id TEXT NOT NULL,
    delay_ticks INTEGER NOT NULL,
    reward INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
