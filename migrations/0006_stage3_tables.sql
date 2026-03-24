-- Migration 0006: Stage 3 Advisory System Tables
-- Purpose: Persist Stage 3 advisory events, council records, and reports.

-- Stage-3 Advice Events (append-only log)
CREATE TABLE IF NOT EXISTS stage3_advice_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source_module TEXT NOT NULL,
    event_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_stage3_events_type ON stage3_advice_events(event_type);

-- Stage-3 Quality Reports
CREATE TABLE IF NOT EXISTS stage3_advice_quality_reports (
    report_id TEXT PRIMARY KEY,
    advice_id TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    composite_score REAL NOT NULL,
    flags_json TEXT NOT NULL,
    created_seeded_ts TEXT NOT NULL
);

-- Stage-3 Council Evaluations
CREATE TABLE IF NOT EXISTS stage3_council_evaluations (
    eval_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    votes_json TEXT NOT NULL,
    disagreement_summary TEXT NOT NULL,
    final_recommendation TEXT NOT NULL,
    created_seeded_ts TEXT NOT NULL
);

-- Stage-3 Action Requests
CREATE TABLE IF NOT EXISTS stage3_action_requests (
    request_id TEXT PRIMARY KEY,
    requester TEXT NOT NULL,
    action_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    approved BOOLEAN NOT NULL,
    created_seeded_ts TEXT NOT NULL
);
