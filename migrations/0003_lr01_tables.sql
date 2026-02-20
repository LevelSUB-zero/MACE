-- Migration 0003: LR-01 Pre-Stage-2 Learning Readiness Tables
-- Purpose: Support MEMCandidate generation, governance decisions, and outcome measurement

-- MEMCandidates - Memory promotion candidates from consolidator
CREATE TABLE IF NOT EXISTS mem_candidates (
    candidate_id TEXT PRIMARY KEY,
    features_json TEXT NOT NULL,
    proposed_key TEXT NOT NULL,
    value TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    consolidator_score REAL NOT NULL,
    mem_snn_score REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mem_candidates_key ON mem_candidates(proposed_key);
CREATE INDEX IF NOT EXISTS idx_mem_candidates_created ON mem_candidates(created_at);

-- Governance Decisions - Approve/Reject records for candidates
CREATE TABLE IF NOT EXISTS governance_decisions (
    decision_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject')),
    reason TEXT NOT NULL,
    heuristic_would_approve INTEGER,  -- 0 or 1, for comparison
    decided_by TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES mem_candidates(candidate_id)
);

CREATE INDEX IF NOT EXISTS idx_governance_candidate ON governance_decisions(candidate_id);
CREATE INDEX IF NOT EXISTS idx_governance_decision ON governance_decisions(decision);

-- Outcome Measurements - Before/after metrics for downstream effect
CREATE TABLE IF NOT EXISTS outcome_measurements (
    outcome_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    query TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('baseline', 'post_promotion')),
    metrics_json TEXT NOT NULL,
    measured_at TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES mem_candidates(candidate_id)
);

CREATE INDEX IF NOT EXISTS idx_outcome_candidate ON outcome_measurements(candidate_id);
CREATE INDEX IF NOT EXISTS idx_outcome_phase ON outcome_measurements(phase);

-- Episodic clusters - Intermediate clustering results
CREATE TABLE IF NOT EXISTS episodic_clusters (
    cluster_id TEXT PRIMARY KEY,
    canonical_key TEXT NOT NULL,
    member_ids_json TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cluster_key ON episodic_clusters(canonical_key);
