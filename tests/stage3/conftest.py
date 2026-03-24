"""
Stage-3 Test Configuration (conftest.py)

Shared fixtures for all Stage-3 tests.
Sets up the database with all required tables before any test runs.
"""

import os
import sys
import sqlite3
import pytest

# Set test DB path BEFORE any imports
DB_PATH = "stage3_test.db"
os.environ["MACE_DB_URL"] = f"sqlite:///{DB_PATH}"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))


@pytest.fixture(scope="session", autouse=True)
def setup_stage3_database():
    """
    Session-scoped fixture to set up the Stage-3 test database.
    Creates all required tables once at the start of the test session.
    """
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stage3_advice_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            source_module TEXT NOT NULL,
            event_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS stage3_advice_quality_reports (
            report_id TEXT PRIMARY KEY,
            advice_id TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            composite_score REAL NOT NULL,
            flags_json TEXT NOT NULL,
            created_seeded_ts TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS stage3_council_evaluations (
            eval_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            votes_json TEXT NOT NULL,
            disagreement_summary TEXT NOT NULL,
            final_recommendation TEXT NOT NULL,
            created_seeded_ts TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS stage3_action_requests (
            request_id TEXT PRIMARY KEY,
            requester TEXT NOT NULL,
            action_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            approved BOOLEAN NOT NULL,
            created_seeded_ts TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    
    # Reload persistence to pick up new DB
    import importlib
    from mace.core import persistence
    importlib.reload(persistence)
    
    yield  # Run tests
    
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
