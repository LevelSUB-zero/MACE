"""
Tests for Stage 3 Advice Ingestion Boundary.
"""

from mace.stage3.advice_schema import AdviceObject
from mace.stage3.advice_ingestion import ingest_advice, validate_advice_object
from mace.stage3.advisory_events import get_events_by_type

def test_ingestion_valid_advice():
    """Ensure clean, signed advice passes ingestion."""
    advice = AdviceObject(
        advice_id="adv_ingest_1",
        content="Consider simplifying the router.",
        advisory_confidence=0.8,
        evidence_refs=[],
        source_module="test",
        created_seeded_ts="tick_1"
    )
    advice.sign()
    
    assert validate_advice_object(advice) is True
    report = ingest_advice(advice)
    assert report is not None
    assert report.advice_id == "adv_ingest_1"
    
    # Should have ingested event
    events = get_events_by_type("ADVICE_INGESTED")
    assert any(e["payload"]["advice_id"] == "adv_ingest_1" for e in events)

def test_ingestion_forbidden_token():
    """Ensure advice with forbidden tokens is rejected and emits violation."""
    advice = AdviceObject(
        advice_id="adv_ingest_2",
        content="We must auto-weight the system or quarantine bad things.",
        advisory_confidence=0.9,
        evidence_refs=[],
        source_module="test",
        created_seeded_ts="tick_2"
    )
    advice.sign()
    
    assert validate_advice_object(advice) is False
    report = ingest_advice(advice)
    assert report is None
    
    # Verify policy violation event
    violations = get_events_by_type("MODULE_POLICY_VIOLATION")
    assert any(e["payload"]["advice_id"] == "adv_ingest_2" for e in violations)

def test_ingestion_bad_signature():
    """Ensure tampered advice fails ingestion."""
    advice = AdviceObject(
        advice_id="adv_ingest_3",
        content="Normal advice.",
        advisory_confidence=0.8,
        evidence_refs=[],
        source_module="test",
        created_seeded_ts="tick_3"
    )
    advice.sign()
    
    # Tamper with content without resigning
    advice.content = "Different advice."
    
    assert validate_advice_object(advice) is False
    report = ingest_advice(advice)
    assert report is None
