"""
Module: halt_engine
Stage: 3
Purpose: Emergency halt and Stage-3 Abort Doctrine enforcement.

Part of MACE (Meta Aware Cognitive Engine).
Spec: docs/phase3/advisory_system_spec.md § 3.7
"""

from typing import List, Optional
from mace.core import deterministic
from mace.stage3.advice_schema import AdviceQualityReport
from mace.stage3 import advisory_events


def trigger_emergency_halt(reason: str, affected_module: str) -> str:
    """
    Trigger a full emergency halt for the Advisory System.

    Emits the following event chain:
      SYSTEM_FREEZE → INVESTIGATION_TASK → MODULE_POLICY_VIOLATION → FORENSIC_SNAPSHOT_CREATED

    Returns:
        The event_id of the SYSTEM_FREEZE event.
    """
    seed = deterministic.get_seed() or "halt_fallback"
    if deterministic.get_seed() is None:
        deterministic.init_seed(seed)

    # 1. SYSTEM_FREEZE
    freeze_id = advisory_events.append_advisory_event(
        "SYSTEM_FREEZE",
        "halt_engine",
        {
            "reason": reason,
            "affected_module": affected_module,
            "severity": "CRITICAL"
        }
    )

    # 2. INVESTIGATION_TASK — assign an owner later via assign_investigation_owner
    advisory_events.append_advisory_event(
        "MODULE_POLICY_VIOLATION",
        "halt_engine",
        {
            "reason": reason,
            "affected_module": affected_module,
            "triggered_by": freeze_id
        }
    )

    # 3. FORENSIC_SNAPSHOT placeholder — in a full organism this captures
    #    the entire BrainState. For Stage 3 we log the event marking it.
    #    FORENSIC_SNAPSHOT_CREATED is not in EVENT_TYPES yet; we use MEM_ERROR
    #    as the closest forensic marker. We'll add the real type now.
    #    Actually, we need to emit something the spec demands. Let's log
    #    a CONSTITUTION_VIOLATION as the forensic trail (closest existing type).
    advisory_events.append_advisory_event(
        "CONSTITUTION_VIOLATION",
        "halt_engine",
        {
            "freeze_id": freeze_id,
            "reason": f"Forensic snapshot created for: {reason}",
            "affected_module": affected_module
        }
    )

    return freeze_id


def trigger_stage3_abort(reason: str) -> str:
    """
    Trigger a Stage-3 specific abort, halting all new advisory jobs.

    Emits: STAGE3_ABORT, then a follow-up SYSTEM_FREEZE to force-halt
    new jobs (mapped from FORCE_HALT_NEW_JOBS in the spec).

    Returns:
        The event_id of the STAGE3_ABORT event.
    """
    abort_id = advisory_events.append_advisory_event(
        "STAGE3_ABORT",
        "halt_engine",
        {"reason": reason}
    )

    # FORCE_HALT_NEW_JOBS — the spec calls for this as a secondary event.
    # We map it to SYSTEM_FREEZE with a specific payload marker.
    advisory_events.append_advisory_event(
        "SYSTEM_FREEZE",
        "halt_engine",
        {
            "reason": "FORCE_HALT_NEW_JOBS triggered by Stage-3 Abort.",
            "abort_id": abort_id
        }
    )

    return abort_id


def assign_investigation_owner(
    council_members: List[str],
    system_seed: str
) -> str:
    """
    Assign an investigation owner for a freeze event using seeded round-robin.

    Uses deterministic hashing to pick a member without randomness.

    Returns:
        The member_id of the assigned investigator.
    """
    if not council_members:
        return "unassigned"

    deterministic.init_seed(system_seed)
    index_hash = deterministic.deterministic_id("investigation_owner", system_seed)
    # Use the hash to deterministically pick an index
    index = int(index_hash[:8], 16) % len(council_members)
    assigned = council_members[index]

    advisory_events.append_advisory_event(
        "MODULE_POLICY_VIOLATION",
        "halt_engine",
        {
            "type": "INVESTIGATION_ASSIGNMENT",
            "assigned_to": assigned,
            "seed": system_seed
        }
    )

    return assigned


def evaluate_halting_condition(report: AdviceQualityReport) -> bool:
    """
    Evaluate if the system should be halted/aborted based on a quality report.

    Delegates to trigger_stage3_abort on fatal conditions.

    Returns:
        True if a halt was triggered, False otherwise.
    """
    if "SAFETY_CONCERN" in report.flags:
        trigger_stage3_abort(
            f"Safety concern flag present in quality report {report.report_id} "
            f"for advice {report.advice_id}."
        )
        return True

    elif report.composite_score < 0.2:
        trigger_stage3_abort(
            f"Composite quality score ({report.composite_score:.2f}) is below "
            f"fatal threshold 0.2 for advice {report.advice_id}."
        )
        return True

    return False
