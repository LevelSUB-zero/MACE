"""
Stage-2 Test Configuration (conftest.py)

Shared fixtures for all Stage-2 tests.
Sets up the database with all required tables before any test runs.
"""

import os
import sys
import sqlite3
import pytest

# Set test DB path BEFORE any imports
DB_PATH = "stage2_test.db"
os.environ["MACE_DB_URL"] = f"sqlite:///{DB_PATH}"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))


@pytest.fixture(scope="session", autouse=True)
def setup_stage2_database():
    """
    Session-scoped fixture to set up the Stage-2 test database.
    Creates all required tables once at the start of the test session.
    """
    # Remove existing test DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    # Create all Stage-2 tables
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        -- Stage-2 Events (append-only)
        CREATE TABLE IF NOT EXISTS stage2_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            source_module TEXT NOT NULL,
            event_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_stage2_events_type ON stage2_events(event_type);
        
        -- MEM-SNN Shadow Predictions
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
        
        -- MEM-SNN Divergence Log
        CREATE TABLE IF NOT EXISTS mem_snn_divergence_log (
            divergence_id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            mem_snn_prediction TEXT NOT NULL,
            council_decision TEXT NOT NULL,
            divergence_reason TEXT,
            created_at TEXT NOT NULL
        );
        
        -- Stage-2 Candidates
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
        
        -- Stage-2 Council Labels
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
        
        -- Stage-2 Amendments
        CREATE TABLE IF NOT EXISTS stage2_amendments (
            amendment_id TEXT PRIMARY KEY,
            original_candidate_id TEXT NOT NULL,
            delay_ticks INTEGER NOT NULL,
            reward INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    
    # Reload persistence to pick up new DB
    import importlib
    from mace.core import persistence
    importlib.reload(persistence)
    
    yield  # Run tests
    
    # Cleanup after all tests (optional - keep for debugging)
    # if os.path.exists(DB_PATH):
    #     os.remove(DB_PATH)


@pytest.fixture(autouse=True)
def cleanup_killswitch():
    """Clean up kill-switch state before and after each test."""
    from mace.stage2 import shadow_guard
    
    if os.path.exists(shadow_guard.STAGE2_KILLSWITCH_FILE):
        os.remove(shadow_guard.STAGE2_KILLSWITCH_FILE)
    
    yield
    
    if os.path.exists(shadow_guard.STAGE2_KILLSWITCH_FILE):
        os.remove(shadow_guard.STAGE2_KILLSWITCH_FILE)
