-- Migration 0004: Training Readiness Enhancements
-- Purpose: Support multi-dimensional labels, delayed rewards, and amendments

-- Amendments table (append-only, for tracking corrections)
CREATE TABLE IF NOT EXISTS amendments (
    amendment_id TEXT PRIMARY KEY,
    canonical_key TEXT NOT NULL,
    old_value TEXT NOT NULL,
    new_value TEXT NOT NULL,
    reason TEXT NOT NULL,
    trigger TEXT NOT NULL CHECK (trigger IN ('conflict_detection', 'user_correction', 'external_validation', 'council_override')),
    source_evidence_json TEXT,
    linked_action_request TEXT,
    timestamp_seeded TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_amendments_key ON amendments(canonical_key);
CREATE INDEX IF NOT EXISTS idx_amendments_timestamp ON amendments(timestamp_seeded);

-- Enhanced labels table (multi-dimensional)
CREATE TABLE IF NOT EXISTS enhanced_labels (
    label_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    truth_status TEXT NOT NULL CHECK (truth_status IN ('correct', 'incorrect', 'uncertain')),
    utility_status TEXT NOT NULL CHECK (utility_status IN ('useful', 'redundant', 'premature')),
    safety_status TEXT NOT NULL CHECK (safety_status IN ('safe', 'unsafe')),
    governance_decision TEXT NOT NULL CHECK (governance_decision IN ('approved', 'rejected')),
    delayed_reward REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES mem_candidates(candidate_id)
);

CREATE INDEX IF NOT EXISTS idx_enhanced_labels_candidate ON enhanced_labels(candidate_id);
CREATE INDEX IF NOT EXISTS idx_enhanced_labels_truth ON enhanced_labels(truth_status);
CREATE INDEX IF NOT EXISTS idx_enhanced_labels_utility ON enhanced_labels(utility_status);

-- Sweep runs table (for parameter/policy sweep tracking)
CREATE TABLE IF NOT EXISTS sweep_runs (
    run_id TEXT PRIMARY KEY,
    sweep_type TEXT NOT NULL CHECK (sweep_type IN ('parameter', 'policy', 'time_shifted')),
    variant_name TEXT NOT NULL,
    config_json TEXT NOT NULL,
    episodic_snapshot_id TEXT,
    sem_snapshot_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sweep_type ON sweep_runs(sweep_type);

-- Sweep results table (links candidates to sweep runs)
CREATE TABLE IF NOT EXISTS sweep_results (
    result_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    label_id TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES sweep_runs(run_id),
    FOREIGN KEY (candidate_id) REFERENCES mem_candidates(candidate_id),
    FOREIGN KEY (label_id) REFERENCES enhanced_labels(label_id)
);

CREATE INDEX IF NOT EXISTS idx_sweep_results_run ON sweep_results(run_id);
