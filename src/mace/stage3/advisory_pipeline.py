"""
Module: advisory_pipeline
Stage: 3
Purpose: Top-level advisory pipeline orchestrator. Wires ingestion,
         quality evaluation, council evaluation, and halt engine into
         a strict DAG.

Part of MACE (Meta Aware Cognitive Engine).
Spec: docs/phase3/advisory_system_spec.md § 3.2
"""

from typing import List, Optional
from dataclasses import dataclass

from mace.stage3.advice_schema import AdviceObject, AdviceQualityReport, CouncilVote, CouncilEvaluationRecord
from mace.stage3.advice_ingestion import ingest_advice
from mace.stage3.council_evaluator import record_council_evaluation
from mace.stage3.halt_engine import evaluate_halting_condition


@dataclass
class PipelineResult:
    """Result of processing advice through the Stage 3 pipeline."""
    status: str
    advice_id: str
    report: Optional[AdviceQualityReport] = None
    council_record: Optional[CouncilEvaluationRecord] = None
    reason: str = ""


def process_advice(
    advice: AdviceObject,
    query_fingerprint: str = "",
    historical_index: Optional[dict] = None,
    votes: Optional[List[CouncilVote]] = None
) -> PipelineResult:
    """
    Main orchestration function for Stage 3 Advisory System.

    Processes advice strictly through the stage boundaries:
        1. validate_advice_object → on fail, halt and emit violation
        2. evaluate_advice → produce AdviceQualityReport
        3. Optionally record_council_evaluation if votes provided
        4. Return advisory result — never modify SEM or router

    Returns:
        A PipelineResult with status, report, and optional council record.
    """
    historical_index = historical_index or {}

    # Step 1 + 2: Ingestion boundary (signatures, forbidden tokens) + quality eval
    report = ingest_advice(advice, query_fingerprint, historical_index)

    if report is None:
        return PipelineResult(
            status="REJECTED_BOUNDARY",
            advice_id=advice.advice_id,
            reason="Failed strict ingestion policy boundary."
        )

    # Step 2b: Halt Engine Safety Net
    if evaluate_halting_condition(report):
        return PipelineResult(
            status="SYSTEM_FROZEN",
            advice_id=advice.advice_id,
            report=report,
            reason="Halt Engine triggered STAGE3_ABORT. Security intervention required."
        )

    # Step 3: Optionally record council evaluation if votes provided
    council_record = None
    if votes is not None and len(votes) > 0:
        council_record = record_council_evaluation(advice.advice_id, votes)

    # Step 4: Successful safe evaluation
    return PipelineResult(
        status="ACCEPTED_AND_EVALUATED",
        advice_id=advice.advice_id,
        report=report,
        council_record=council_record,
        reason="Advice evaluated successfully."
    )
