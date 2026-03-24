"""
Tests for Stage 3 Advisory Events.
"""

import pytest
from mace.core import deterministic, signing
from mace.stage3.advisory_events import append_advisory_event, EVENT_TYPES

def test_append_advisory_event_success():
    """Ensure we can generate and persist an event with valid type."""
    deterministic.init_seed("test_event_seed")
    
    event_id = append_advisory_event(
        event_type="ADVICE_GENERATED",
        source_module="test_runner",
        payload={"msg": "hello"},
        evidence_ids=["ev1", "ev2"]
    )
    
    assert event_id is not None
    assert isinstance(event_id, str)
    
    # We should be able to fetch it from the DB
    from mace.core.persistence import get_connection, execute_query, fetch_one
    conn = get_connection()
    cur = execute_query(conn, "SELECT * FROM stage3_advice_events WHERE event_id = ?", (event_id,))
    row = fetch_one(cur)
    conn.close()
    
    assert row is not None
    assert row["event_type"] == "ADVICE_GENERATED"
    assert row["source_module"] == "test_runner"
    
def test_append_advisory_event_invalid_type():
    """Ensure it strictly blocks unknown event types."""
    with pytest.raises(ValueError):
        append_advisory_event(
            event_type="BOGUS_EVENT",
            source_module="test",
            payload={}
        )
