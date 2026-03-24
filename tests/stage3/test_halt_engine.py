"""
Tests for Stage 3 Halt Engine.

Covers spec § 3.7:
  - Emergency halt emits SYSTEM_FREEZE, MODULE_POLICY_VIOLATION (investigation),
    CONSTITUTION_VIOLATION (forensic snapshot)
  - Stage-3 Abort emits STAGE3_ABORT + SYSTEM_FREEZE (FORCE_HALT_NEW_JOBS)
  - assign_investigation_owner uses seeded round-robin
  - evaluate_halting_condition delegates to trigger_stage3_abort
"""

from mace.core import deterministic
from mace.stage3.halt_engine import (
    trigger_emergency_halt,
    trigger_stage3_abort,
    assign_investigation_owner,
    evaluate_halting_condition
)
from mace.stage3.advice_schema import AdviceQualityReport
from mace.stage3.advisory_events import get_events_by_type


def test_emergency_halt_emits_all_required_events():
    """Emergency halt emits SYSTEM_FREEZE, MODULE_POLICY_VIOLATION, CONSTITUTION_VIOLATION."""
    deterministic.init_seed("halt_emergency_seed")

    freeze_id = trigger_emergency_halt(
        reason="Critical safety failure detected",
        affected_module="advice_quality"
    )

    assert freeze_id is not None

    # SYSTEM_FREEZE emitted
    freezes = get_events_by_type("SYSTEM_FREEZE")
    assert any(
        e["payload"].get("reason") == "Critical safety failure detected"
        for e in freezes
    )

    # MODULE_POLICY_VIOLATION emitted (investigation task)
    violations = get_events_by_type("MODULE_POLICY_VIOLATION")
    assert any(
        e["payload"].get("triggered_by") == freeze_id
        for e in violations
    )

    # CONSTITUTION_VIOLATION emitted (forensic snapshot)
    forensics = get_events_by_type("CONSTITUTION_VIOLATION")
    assert any(
        e["payload"].get("freeze_id") == freeze_id
        for e in forensics
    )


def test_stage3_abort_emits_abort_and_force_halt():
    """Stage-3 Abort emits STAGE3_ABORT + SYSTEM_FREEZE (FORCE_HALT_NEW_JOBS)."""
    deterministic.init_seed("halt_abort_seed")

    abort_id = trigger_stage3_abort(reason="Composite score below threshold")

    assert abort_id is not None

    # STAGE3_ABORT emitted
    aborts = get_events_by_type("STAGE3_ABORT")
    assert any(
        e["payload"].get("reason") == "Composite score below threshold"
        for e in aborts
    )

    # SYSTEM_FREEZE emitted (FORCE_HALT_NEW_JOBS)
    freezes = get_events_by_type("SYSTEM_FREEZE")
    assert any(
        "FORCE_HALT_NEW_JOBS" in e["payload"].get("reason", "")
        for e in freezes
    )


def test_assign_investigation_owner_deterministic():
    """Seeded round-robin produces deterministic assignment."""
    members = ["guard", "policy", "utility", "ethics"]

    owner1 = assign_investigation_owner(members, "seed_abc")
    owner2 = assign_investigation_owner(members, "seed_abc")

    assert owner1 == owner2  # Same seed → same assignment
    assert owner1 in members

    # Different seed → potentially different assignment (deterministic but different)
    owner3 = assign_investigation_owner(members, "seed_xyz")
    assert owner3 in members


def test_assign_investigation_owner_empty_list():
    """Empty council → 'unassigned'."""
    owner = assign_investigation_owner([], "any_seed")
    assert owner == "unassigned"


def test_evaluate_halting_low_score():
    """evaluate_halting_condition delegates to trigger_stage3_abort on low score."""
    deterministic.init_seed("halt_eval_low")
    report = AdviceQualityReport(
        report_id="rep_eval_1",
        advice_id="adv_eval_1",
        factuality=0.1, relevance=0.1, coherence=0.1, provenance=0.1,
        uncertainty=0.0, novelty=0.1, safety="safe", empirical_utility=0.1,
        composite_score=0.15,
        flags=[],
        created_seeded_ts="tick_eval_1",
        derived_from_evidence=False
    )
    report.sign()

    assert evaluate_halting_condition(report) is True

    # Should have emitted STAGE3_ABORT + SYSTEM_FREEZE
    aborts = get_events_by_type("STAGE3_ABORT")
    assert any("adv_eval_1" in e["payload"].get("reason", "") for e in aborts)


def test_evaluate_halting_safety_concern():
    """evaluate_halting_condition triggers on SAFETY_CONCERN flag."""
    deterministic.init_seed("halt_eval_safety")
    report = AdviceQualityReport(
        report_id="rep_eval_2",
        advice_id="adv_eval_2",
        factuality=0.9, relevance=0.9, coherence=0.9, provenance=0.9,
        uncertainty=0.0, novelty=0.9, safety="unsafe", empirical_utility=0.9,
        composite_score=0.95,
        flags=["SAFETY_CONCERN"],
        created_seeded_ts="tick_eval_2",
        derived_from_evidence=False
    )
    report.sign()

    assert evaluate_halting_condition(report) is True


def test_evaluate_halting_normal_no_halt():
    """Normal report does not trigger halt."""
    deterministic.init_seed("halt_eval_normal")
    report = AdviceQualityReport(
        report_id="rep_eval_3",
        advice_id="adv_eval_3",
        factuality=0.9, relevance=0.9, coherence=0.9, provenance=0.9,
        uncertainty=0.0, novelty=0.9, safety="safe", empirical_utility=0.9,
        composite_score=0.95,
        flags=[],
        created_seeded_ts="tick_eval_3",
        derived_from_evidence=False
    )
    report.sign()

    assert evaluate_halting_condition(report) is False
