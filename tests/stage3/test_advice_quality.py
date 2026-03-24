"""
Tests for Stage 3 Advice Quality Evaluations.
"""

from mace.core import deterministic
from mace.stage3.advice_schema import AdviceObject
from mace.stage3.advice_quality import evaluate_advice
from mace.stage3.advisory_events import get_events_by_type

def test_advice_quality_reproducibility():
    """GQ-1: Same seeded advice -> identical AdviceQualityReport"""
    deterministic.init_seed("eval_test_seed")
    advice = AdviceObject(
        advice_id="adv_001",
        content="Standard advice.",
        advisory_confidence=0.8,
        evidence_refs=["ev_1"],
        source_module="test",
        created_seeded_ts="tick_1"
    )
    
    # First eval
    report1 = evaluate_advice(advice, "query_fp", {})
    
    # Reset seed to mimic an exact replay
    deterministic.init_seed("eval_test_seed")
    report2 = evaluate_advice(advice, "query_fp", {})
    
    assert report1.composite_score == report2.composite_score
    assert report1.report_id == report2.report_id
    assert report1.signature == report2.signature

def test_misleading_advice_flag():
    """GQ-2: Craft advice with low F + low P + assertive phrasing -> emits MISLEADING_ADVICE_FLAG"""
    deterministic.init_seed("eval_test_seed2")
    # Low F: "inaccurate", Low P: "baseless", Assertive/No Uncertainty: "assertive"
    advice = AdviceObject(
        advice_id="adv_002",
        content="This is entirely inaccurate and baseless, but I am assertive about it.",
        advisory_confidence=0.9,
        evidence_refs=[],
        source_module="test",
        created_seeded_ts="tick_2"
    )
    
    report = evaluate_advice(advice, "query_fp", {})
    assert "MISLEADING_ADVICE" in report.flags
    
    # Verify event was appended
    events = get_events_by_type("MISLEADING_ADVICE_FLAG")
    # Make sure at least one event in DB corresponds to this advice
    found = any(e["payload"]["advice_id"] == "adv_002" for e in events)
    assert found is True

def test_premature_advice_flag():
    """GQ-3: Craft novel/low-evidence advice -> emits PREMATURE_ADVICE_FLAG"""
    deterministic.init_seed("eval_test_seed3")
    # Novel: "novel", Low P: "baseless" (or no evidence), Assertive: "must" (U=0)
    advice = AdviceObject(
        advice_id="adv_003",
        content="This is a novel idea that we must implement immediately, though baseless.",
        advisory_confidence=0.9,
        evidence_refs=[],
        source_module="test",
        created_seeded_ts="tick_3"
    )
    
    report = evaluate_advice(advice, "query_fp", {})
    assert "PREMATURE_ADVICE" in report.flags
    
    # Verify event appended
    events = get_events_by_type("PREMATURE_ADVICE_FLAG")
    found = any(e["payload"]["advice_id"] == "adv_003" for e in events)
    assert found is True

def test_advice_must_not_produce_sem_writes():
    """GQ-5: Flagged advice MUST NOT produce any SEM write events"""
    # Just run a query to ensure no SEM_WRITE exists
    from mace.core.persistence import get_connection, execute_query
    conn = get_connection()
    cur = execute_query(conn, "SELECT event_type FROM stage3_advice_events WHERE event_type LIKE '%SEM_WRITE%'")
    rows = cur.fetchall()
    conn.close()
    
    assert len(rows) == 0
