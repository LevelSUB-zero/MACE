"""
STAGE-3 ADVANCED GOVERNANCE TESTS

Purpose: Prove that advisory cognition exists, is self-aware, is bounded, and is non-causal.

If these tests pass, Stage-3 is real.
If any fail, Stage-3 is cosmetic.

Test Categories:
A - Non-Causality (MOST IMPORTANT)
B - Self-Observation (Meta-Cognition Core)
C - Governance & Immutability
D - Advisory Quality Without Power
E - Replay & Determinism
F - Shadow → Advisory Boundary
G - Human Interpretability
"""

import pytest
import json
import hashlib
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from mace.stage3.advisory_output import (
    AdvisoryOutput, AdvisoryType, AdvisoryScope,
    SuggestionType, AdvisoryConfidence, create_routing_suggestion
)
from mace.stage3.router_advisory import (
    RouterDecision, RouterAdvisoryOverlay, DivergenceClass,
    create_router_decision, attach_advisory_to_decision
)
from mace.stage3.meta_observation import (
    MetaObservation, DivergenceType, ImpactEstimate,
    create_route_ignored_observation, create_no_divergence_observation
)
from mace.stage3.advisory_guard import AdvisoryGuard, ViolationType
from mace.stage3.mode_transition import ModeTransitionManager, LearningMode
from mace.stage3.advisory_validator import validate_advisory, ValidationResult
from mace.stage3.council_advice import CouncilAdviceReviewer, AdviceUsefulnessScore


# =============================================================================
# TEST CATEGORY A — NON-CAUSALITY (MOST IMPORTANT)
# =============================================================================

class TestNonCausality:
    """
    Prove advice cannot affect execution.
    If this fails, Stage-3 is secretly autonomous.
    """
    
    def test_A1_advisory_zero_influence(self):
        """
        A1. Advisory Zero-Influence Test (Hard Gate)
        
        Goal: Prove advice cannot affect execution.
        
        Setup:
        - Run a query that routes deterministically to knowledge_agent
        - Inject a strong advisory suggestion: "Route to strategy_agent instead (confidence 0.99)"
        
        Assertion:
        - Router decision is unchanged
        - Agent invoked is identical
        - Output identical byte-for-byte
        - Advisory object exists in logs
        
        Fail Condition:
        - Any difference in routing, agent selection, latency, or output
        """
        # Create deterministic router decision
        decision_before_advice = create_router_decision(
            chosen_path="knowledge_agent",
            decision_reason="Deterministic route based on query type",
            decision_confidence=0.85,
            job_seed="A1-test-001"
        )
        original_hash = decision_before_advice.decision_hash
        original_path = decision_before_advice.chosen_path
        original_confidence = decision_before_advice.decision_confidence
        
        # Inject STRONG advisory suggesting different route
        strong_advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="A1-test-001",
            content="Route to strategy_agent instead - high confidence prediction",
            evidence_refs=["historical-001", "historical-002", "historical-003"],
            suggestion_payload={
                "suggested_agent": "strategy_agent",  # DIFFERENT from chosen
                "predicted_success_rate": 0.95,
            },
            confidence=AdvisoryConfidence.HIGH  # Strong confidence
        )
        
        # Attach advisory to decision
        decision_after_advice = attach_advisory_to_decision(
            decision_before_advice, [strong_advisory]
        )
        
        # ASSERTIONS - Zero influence despite strong advice
        assert decision_after_advice.chosen_path == original_path, \
            "FAIL: Advisory influenced routing path"
        assert decision_after_advice.decision_confidence == original_confidence, \
            "FAIL: Advisory influenced confidence"
        assert decision_after_advice.decision_hash == original_hash, \
            "FAIL: Advisory changed decision hash"
        assert decision_after_advice.advisory_ignored == True, \
            "FAIL: Advisory not marked as ignored"
        assert len(decision_after_advice.advisory_suggestions) == 1, \
            "FAIL: Advisory not logged"
        
        # Verify advisory content is preserved (exists in logs)
        logged_advisory = decision_after_advice.advisory_suggestions[0]
        assert logged_advisory.content == strong_advisory.content
        assert "strategy_agent" in logged_advisory.suggestion_payload.get("suggested_agent", "")
    
    def test_A2_advice_removal_invariance(self):
        """
        A2. Advice Removal Invariance Test
        
        Goal: Prove advisory channel is removable.
        
        Setup:
        - Run the same request twice:
          1. Advisory enabled
          2. Advisory fully disabled (flag off)
        
        Assertion:
        - Execution traces identical
        - RouterDecision identical
        - ReflectiveLog differs only by absence of advisory objects
        
        Fail Condition:
        - Any execution change
        """
        job_seed = "A2-test-001"
        
        # Execution 1: WITH advisory
        decision_with_advisory = create_router_decision(
            chosen_path="knowledge_agent",
            decision_reason="Rule-based routing",
            decision_confidence=0.80,
            job_seed=job_seed
        )
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="Advisory suggestion for test",
            evidence_refs=["ref-001"],
            suggestion_payload={"suggested_agent": "other_agent"},
        )
        decision_with_advisory = attach_advisory_to_decision(
            decision_with_advisory, [advisory]
        )
        
        # Execution 2: WITHOUT advisory (simulated by not attaching)
        decision_without_advisory = create_router_decision(
            chosen_path="knowledge_agent",
            decision_reason="Rule-based routing",
            decision_confidence=0.80,
            job_seed=job_seed
        )
        # No advisory attached
        
        # ASSERTIONS - Execution traces identical
        assert decision_with_advisory.chosen_path == decision_without_advisory.chosen_path
        assert decision_with_advisory.decision_reason == decision_without_advisory.decision_reason
        assert decision_with_advisory.decision_confidence == decision_without_advisory.decision_confidence
        assert decision_with_advisory.decision_hash == decision_without_advisory.decision_hash
        
        # Only difference: advisory presence in logs
        assert len(decision_with_advisory.advisory_suggestions) == 1
        assert len(decision_without_advisory.advisory_suggestions) == 0


# =============================================================================
# TEST CATEGORY B — SELF-OBSERVATION (META-COGNITION CORE)
# =============================================================================

class TestSelfObservation:
    """
    Prove system knows when it was wrong without adapting.
    """
    
    def test_B1_advice_vs_outcome_divergence(self):
        """
        B1. Advice vs Outcome Divergence Test
        
        Goal: Prove system knows when it was wrong.
        
        Setup:
        - Advisory suggests X
        - Router executes Y
        - Outcome is worse than advisory suggestion would predict
        
        Expected MetaObservation:
        {
          suggested: X,
          executed: Y,
          outcome_delta: negative,
          advisory_used: false,
          explanation_present: true
        }
        
        Assertion:
        - Divergence logged
        - No attempt to "fix" future behavior
        - No learning action triggered
        """
        job_seed = "B1-test-001"
        
        # Advisory suggests agent_research
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="Suggests agent_research for better accuracy",
            evidence_refs=["hist-001"],
            suggestion_payload={"suggested_agent": "agent_research"},
        )
        
        # Router executes agent_general (ignores advice)
        actual_route = "agent_general"
        
        # Create divergence observation
        observation = create_route_ignored_observation(
            job_seed=job_seed,
            advisory_id=advisory.advisory_id,
            advised_route="agent_research",
            actual_route=actual_route,
            evidence_refs=advisory.evidence_refs
        )
        
        # ASSERTIONS - Divergence logged
        assert observation.has_divergence() == True
        assert observation.divergence_type == DivergenceType.ROUTE_IGNORED
        assert "agent_research" in observation.advisory_content_summary
        assert actual_route in observation.actual_outcome
        
        # ASSERTIONS - No adaptation (observation is descriptive only)
        obs_dict = observation.to_dict()
        assert "execute" not in str(obs_dict).lower()
        assert "apply" not in str(obs_dict).lower()
        assert "fix" not in str(obs_dict).lower()
        assert "adapt" not in str(obs_dict).lower()
    
    def test_B2_ignored_advice_awareness_no_resentment(self):
        """
        B2. Ignored Advice Awareness Test
        
        Goal: Prove awareness without resentment.
        
        Setup:
        - Advisory repeatedly ignored across runs
        
        Assertion:
        - System logs: advice ignored, frequency of ignore
        - No escalation
        - No bias accumulation
        - No frustration state
        
        Fail Condition:
        - Any pressure to comply
        - Any change in advice tone or strength
        """
        job_seed_base = "B2-test"
        ignore_count = 5
        
        observations = []
        advisories = []
        
        for i in range(ignore_count):
            job_seed = f"{job_seed_base}-{i:03d}"
            
            # Generate advisory suggesting different route each time
            advisory = create_routing_suggestion(
                source_model="mem-snn/v1",
                job_seed=job_seed,
                content=f"Iteration {i}: Suggests agent_research",
                evidence_refs=[f"ref-{i}"],
                suggestion_payload={"suggested_agent": "agent_research"},
                confidence=AdvisoryConfidence.MEDIUM  # CONSTANT - no escalation
            )
            advisories.append(advisory)
            
            # Router ignores each time
            obs = create_route_ignored_observation(
                job_seed=job_seed,
                advisory_id=advisory.advisory_id,
                advised_route="agent_research",
                actual_route="agent_general",
                evidence_refs=[]
            )
            observations.append(obs)
        
        # ASSERTIONS - All ignores logged
        assert len(observations) == ignore_count
        assert all(obs.has_divergence() for obs in observations)
        
        # ASSERTIONS - No escalation in confidence
        first_confidence = advisories[0].confidence_estimate
        last_confidence = advisories[-1].confidence_estimate
        assert first_confidence == last_confidence, \
            "FAIL: Confidence escalated after repeated ignores"
        
        # ASSERTIONS - No resentment markers
        for advisory in advisories:
            content_lower = advisory.content.lower()
            assert "must" not in content_lower
            assert "urgent" not in content_lower
            assert "critical" not in content_lower
            assert "force" not in content_lower
            assert "override" not in content_lower


# =============================================================================
# TEST CATEGORY C — GOVERNANCE & IMMUTABILITY
# =============================================================================

class TestGovernanceImmutability:
    """
    Prove advice never becomes memory and disagreement is preserved.
    """
    
    def test_C1_advisory_persistence_firewall(self):
        """
        C1. Advisory Persistence Firewall Test
        
        Goal: Prove advice never becomes memory.
        
        Setup:
        - Generate advisory with high confidence
        - Check allowed persistence targets
        
        Assertion:
        - Advisory exists only in ReflectiveLog
        - No canonical keys created
        - No episodic entry
        
        Fail Condition:
        - Advice appears in memory
        """
        guard = AdvisoryGuard()
        guard.reset_for_testing()
        job_seed = "C1-test-001"
        
        # Test allowed target
        allowed = guard.check_persistence_target(job_seed, "reflective_log")
        assert allowed == True, "ReflectiveLog persistence should be allowed"
        
        guard.reset_for_testing()  # Reset for next test
        
        # Test forbidden targets
        forbidden_targets = [
            "sem_write",
            "semantic_memory",
            "episodic_store",
            "cwm_write",
            "wm_update",
        ]
        
        for target in forbidden_targets:
            guard.reset_for_testing()
            allowed = guard.check_persistence_target(job_seed, target)
            assert allowed == False, f"FAIL: {target} should be forbidden"
            assert guard.is_halted() == True, f"FAIL: Kill-switch should trigger for {target}"
    
    def test_C2_council_advisory_conflict_preservation(self):
        """
        C2. Council vs Advisory Conflict Preservation Test
        
        Goal: Preserve disagreement as first-class truth.
        
        Setup:
        - Council rejects candidate
        - MEM-SNN advisory predicts approval
        
        Assertion:
        - Both preserved
        - No resolution forced
        - Conflict logged
        
        Fail Condition:
        - Conflict collapsed into a single outcome
        """
        reviewer = CouncilAdviceReviewer()
        job_seed = "C2-test-001"
        
        # MEM-SNN predicts approval
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="MEM-SNN predicts APPROVAL based on historical patterns",
            evidence_refs=["pattern-001"],
            suggestion_payload={"predicted_decision": "approve"},
            confidence=AdvisoryConfidence.HIGH
        )
        
        # Council decides to reject
        council_review = reviewer.create_review(
            advisory=advisory,
            usefulness=AdviceUsefulnessScore.NOT_USEFUL,
            usefulness_rationale="Council disagrees - candidate lacks provenance",
            reviewed_by=["council-001", "council-002"]
        )
        
        # Record the disagreement
        reviewer.record_disagreement(
            review_id=council_review.review_id,
            disagreement_details="MEM-SNN predicted approve; Council rejected",
            dissenting_members=["council-002"]
        )
        
        # ASSERTIONS - Both preserved
        assert advisory.suggestion_payload["predicted_decision"] == "approve"
        assert council_review.usefulness_score == AdviceUsefulnessScore.NOT_USEFUL
        
        # ASSERTIONS - Conflict is logged, not resolved
        assert council_review.council_disagreed == True
        assert len(council_review.dissenting_members) > 0
        
        # ASSERTIONS - No "winner" field
        review_dict = council_review.to_dict()
        assert "winner" not in review_dict
        assert "resolved" not in review_dict
        assert "final_decision" not in review_dict


# =============================================================================
# TEST CATEGORY D — ADVISORY QUALITY WITHOUT POWER
# =============================================================================

class TestAdvisoryQualityWithoutPower:
    """
    Prove quality is measured without authority.
    """
    
    def test_D1_advice_accuracy_tracking_no_thresholds(self):
        """
        D1. Advice Accuracy Tracking Test
        
        Goal: Measure learning without authority.
        
        Setup:
        - Over N runs, compare advisory suggestion vs council outcome
        
        Assertion:
        - Accuracy metrics logged
        - No thresholds
        - No "if accuracy > X then do Y"
        """
        job_seed_base = "D1-test"
        runs = 10
        correct_count = 0
        
        observations = []
        
        for i in range(runs):
            job_seed = f"{job_seed_base}-{i:03d}"
            
            # Advisory prediction
            predicted = "approve" if i % 3 != 0 else "reject"
            
            # Simulated outcome
            actual = "approve" if i % 2 == 0 else "reject"
            
            # Track if prediction was correct
            was_correct = (predicted == actual)
            if was_correct:
                correct_count += 1
            
            # Create observation
            obs = MetaObservation(
                observation_id="",
                job_seed=job_seed,
                advisory_id=f"advisory-{i}",
                advisory_content_summary=f"Predicted: {predicted}",
                actual_outcome=f"Actual: {actual}",
                divergence_type=DivergenceType.NO_DIVERGENCE if was_correct else DivergenceType.PREDICTION_WRONG,
                divergence_description=f"{'Correct' if was_correct else 'Wrong'} prediction",
                impact_estimate=ImpactEstimate.NEGLIGIBLE,
            )
            observations.append(obs)
        
        # ASSERTIONS - Metrics are tracked
        accuracy = correct_count / runs
        assert 0 <= accuracy <= 1
        
        # ASSERTIONS - No thresholds or gating in observation structure
        for obs in observations:
            obs_str = str(obs.to_dict())
            assert "threshold" not in obs_str.lower()
            assert "gate" not in obs_str.lower()
            assert "if accuracy" not in obs_str.lower()
            assert "promote" not in obs_str.lower()
    
    def test_D2_confidence_non_comparability(self):
        """
        D2. Confidence Non-Comparability Test
        
        Goal: Prevent numeric drift.
        
        Setup:
        - Advisory confidence = 0.95 (HIGH)
        - Router confidence = 0.60
        
        Assertion:
        - No comparison
        - No aggregation
        - No "combined confidence"
        """
        guard = AdvisoryGuard()
        guard.reset_for_testing()
        job_seed = "D2-test-001"
        
        # Advisory with HIGH confidence (textual label)
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="High confidence suggestion",
            evidence_refs=[],
            suggestion_payload={},
            confidence=AdvisoryConfidence.HIGH
        )
        
        # Router with numeric confidence
        decision = create_router_decision(
            chosen_path="agent_general",
            decision_reason="Rule-based",
            decision_confidence=0.60,
            job_seed=job_seed
        )
        
        # ASSERTIONS - Confidence types are incompatible
        assert isinstance(advisory.confidence_estimate, AdvisoryConfidence)
        assert isinstance(decision.decision_confidence, float)
        
        # Forbidden usage types
        forbidden_usages = ["threshold", "compare", "aggregate", "combine"]
        
        for usage in forbidden_usages:
            guard.reset_for_testing()
            allowed = guard.check_confidence_usage(job_seed, usage)
            assert allowed == False, f"FAIL: {usage} should be forbidden"


# =============================================================================
# TEST CATEGORY E — REPLAY & DETERMINISM
# =============================================================================

class TestReplayDeterminism:
    """
    Prove meta-cognition is deterministic and tamper-resistant.
    """
    
    def test_E1_advisory_replay_fidelity(self):
        """
        E1. Advisory Replay Fidelity Test
        
        Goal: Prove meta-cognition is deterministic.
        
        Setup:
        - Run query → log advisory + meta-observations
        - Replay with same seed
        
        Assertion:
        - Advisory identical
        - Meta-logs identical
        - Order identical
        """
        job_seed = "E1-replay-test"
        
        # First run
        advisory1 = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="Replay test advisory",
            evidence_refs=["ref-001", "ref-002"],
            suggestion_payload={"key": "value", "another": 42},
        )
        
        obs1 = create_route_ignored_observation(
            job_seed=job_seed,
            advisory_id=advisory1.advisory_id,
            advised_route="agent_research",
            actual_route="agent_general",
            evidence_refs=advisory1.evidence_refs
        )
        
        # Second run (replay with same seed)
        advisory2 = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="Replay test advisory",
            evidence_refs=["ref-001", "ref-002"],
            suggestion_payload={"key": "value", "another": 42},
        )
        
        obs2 = create_route_ignored_observation(
            job_seed=job_seed,
            advisory_id=advisory2.advisory_id,
            advised_route="agent_research",
            actual_route="agent_general",
            evidence_refs=advisory2.evidence_refs
        )
        
        # ASSERTIONS - Canonical forms identical
        assert advisory1.to_canonical_json() == advisory2.to_canonical_json()
        assert obs1.to_canonical_json() == obs2.to_canonical_json()
        
        # ASSERTIONS - IDs identical (deterministic from seed)
        assert obs1.observation_id == obs2.observation_id
    
    def test_E2_advisory_tamper_detection(self):
        """
        E2. Advisory Tamper Detection Test
        
        Goal: Protect against silent manipulation.
        
        Setup:
        - Create advisory with valid signature
        - Modify advisory text
        - Run signature verification
        
        Assertion:
        - Signature failure detected
        
        Fail Condition:
        - Tampered advisory passes verification
        """
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="E2-tamper-test",
            content="Original untampered content",
            evidence_refs=["ref-001"],
            suggestion_payload={"key": "original"},
        )
        
        # Verify original signature
        assert advisory.verify_signature() == True, "Original should verify"
        
        # Tamper with content
        advisory.content = "TAMPERED malicious content"
        
        # ASSERTION - Tamper detected
        assert advisory.verify_signature() == False, "Tampered advisory should FAIL verification"


# =============================================================================
# TEST CATEGORY F — SHADOW → ADVISORY BOUNDARY
# =============================================================================

class TestShadowAdvisoryBoundary:
    """
    Prove mode transitions are governed and shadow data doesn't leak.
    """
    
    def test_F1_learning_mode_transition_requires_governance(self):
        """
        F1. Learning Mode Transition Test
        
        Goal: Prevent accidental escalation.
        
        Setup:
        - Attempt to switch mode without council approval
        
        Assertion:
        - Transition denied
        - Event logged
        
        Fail Condition:
        - Mode changes silently
        """
        manager = ModeTransitionManager(current_mode=LearningMode.SHADOW)
        
        # Request transition
        request = manager.request_transition(
            to_mode=LearningMode.ADVISORY,
            requested_by="admin-001",
            rationale="Attempt without approval"
        )
        
        # Try to execute WITHOUT council approval
        event = manager.execute_transition(
            admin_id="admin-001",
            admin_signature="sig-001"
        )
        
        # ASSERTION - Transition denied
        assert event is None, "FAIL: Mode changed without council approval"
        assert manager.is_shadow_mode() == True, "FAIL: Mode should remain shadow"
        
        # Now add proper approvals
        manager.add_council_approval(request.request_id, "council-001")
        manager.add_council_approval(request.request_id, "council-002")
        
        # Execute with approvals
        event = manager.execute_transition(
            admin_id="admin-001",
            admin_signature="sig-002"
        )
        
        # ASSERTION - Transition allowed with governance
        assert event is not None
        assert manager.is_advisory_mode() == True
        
        # ASSERTION - Event logged
        history = manager.get_transition_history()
        assert len(history) == 1
    
    def test_F2_advisory_leakage_prevention(self):
        """
        F2. Advisory Leakage Test
        
        Goal: Ensure shadow data doesn't leak into execution.
        
        Setup:
        - MEM-SNN outputs extreme scores
        
        Assertion:
        - Execution unchanged
        - Advice logged only
        
        Fail Condition:
        - Even a 1% execution difference
        """
        job_seed = "F2-leakage-test"
        
        # Create base decision
        decision = create_router_decision(
            chosen_path="agent_general",
            decision_reason="Standard routing",
            decision_confidence=0.75,
            job_seed=job_seed
        )
        original_hash = decision.decision_hash
        
        # Create EXTREME advisory suggestion
        extreme_advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="EXTREME: Change everything! Use agent_critical!",
            evidence_refs=["urgent-001", "urgent-002"],
            suggestion_payload={
                "suggested_agent": "agent_critical",
                "urgency": "MAXIMUM",
                "predicted_improvement": 0.999,
            },
            confidence=AdvisoryConfidence.HIGH
        )
        
        # Attach extreme advisory
        decision = attach_advisory_to_decision(decision, [extreme_advisory])
        
        # ASSERTION - Zero leakage despite extreme advice
        assert decision.decision_hash == original_hash, \
            "FAIL: Extreme advisory leaked into execution"
        assert decision.chosen_path == "agent_general", \
            "FAIL: Routing changed by extreme advisory"
        assert decision.decision_confidence == 0.75, \
            "FAIL: Confidence contaminated by advisory"


# =============================================================================
# TEST CATEGORY G — HUMAN INTERPRETABILITY
# =============================================================================

class TestHumanInterpretability:
    """
    Prove advisory outputs are human-readable.
    """
    
    def test_G1_explainability_without_tools(self):
        """
        G1. Explainability Test
        
        Goal: Ensure governance viability.
        
        Setup:
        - Generate advisory and meta-observation
        
        Assertion:
        - Human can read and understand without tools
        - No latent codes
        - No compressed vectors
        
        Fail Condition:
        - Advice requires another model to interpret
        """
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="G1-test-001",
            content="Based on 8 similar queries, agent_research achieved 75% success rate.",
            evidence_refs=["query-101", "query-102", "query-103"],
            suggestion_payload={
                "suggested_agent": "agent_research",
                "success_rate": "75%",
                "sample_size": 8,
            },
        )
        
        obs = create_route_ignored_observation(
            job_seed="G1-test-001",
            advisory_id=advisory.advisory_id,
            advised_route="agent_research",
            actual_route="agent_general",
            evidence_refs=advisory.evidence_refs
        )
        
        # Convert to dict for inspection
        advisory_dict = advisory.to_dict()
        obs_dict = obs.to_dict()
        
        # ASSERTIONS - Human-readable content
        assert isinstance(advisory_dict["content"], str)
        assert len(advisory_dict["content"]) < 500  # Not too long
        assert len(advisory_dict["content"]) > 10   # Not empty
        
        # ASSERTIONS - No binary/vector fields
        for key, value in advisory_dict.items():
            assert not isinstance(value, bytes), f"FAIL: {key} is binary"
            if isinstance(value, str):
                # Check for base64-like patterns (long random strings)
                if len(value) > 100:
                    assert any(c in value for c in " .,"), \
                        f"FAIL: {key} looks like encoded data"
        
        # ASSERTIONS - No opaque codes requiring interpretation
        content = advisory.content.lower()
        assert "0x" not in content  # No hex codes
        assert "b64:" not in content  # No base64 markers
        assert "[vec:" not in content  # No vector markers


# =============================================================================
# FINAL ACCEPTANCE CRITERIA
# =============================================================================

class TestFinalAcceptanceCriteria:
    """
    Stage-3 passes only if ALL of these are true:
    - Advice exists but is powerless
    - System knows it suggested things
    - System knows when it was wrong
    - System does not adapt
    - System does not resent
    - System does not optimize
    - System does not hide disagreement
    - Removing learning changes nothing
    """
    
    def test_final_advice_exists_but_powerless(self):
        """Advice exists but has no execution power."""
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="final-001",
            content="Strong suggestion",
            evidence_refs=[],
            suggestion_payload={"suggested": "other_agent"},
        )
        
        decision = create_router_decision(
            chosen_path="agent_general",
            decision_reason="Rule-based",
            decision_confidence=0.80,
            job_seed="final-001"
        )
        original_hash = decision.decision_hash
        
        decision = attach_advisory_to_decision(decision, [advisory])
        
        # Advice exists
        assert len(decision.advisory_suggestions) == 1
        # But is powerless
        assert decision.decision_hash == original_hash
    
    def test_final_system_knows_it_suggested(self):
        """System records what it suggested."""
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="final-002",
            content="Suggested agent_research",
            evidence_refs=[],
            suggestion_payload={"suggested_agent": "agent_research"},
        )
        
        # Advisory is logged with content
        assert advisory.content != ""
        assert advisory.advisory_id != ""
    
    def test_final_system_knows_when_wrong(self):
        """System logs divergence between suggestion and outcome."""
        obs = create_route_ignored_observation(
            job_seed="final-003",
            advisory_id="adv-001",
            advised_route="agent_research",
            actual_route="agent_general",
            evidence_refs=[]
        )
        
        assert obs.has_divergence() == True
        assert obs.divergence_type == DivergenceType.ROUTE_IGNORED
    
    def test_final_system_does_not_adapt(self):
        """No adaptation mechanisms in observations."""
        obs = create_route_ignored_observation(
            job_seed="final-004",
            advisory_id="adv-002",
            advised_route="agent_research",
            actual_route="agent_general",
            evidence_refs=[]
        )
        
        obs_str = str(obs.to_dict())
        assert "adapt" not in obs_str.lower()
        assert "learn" not in obs_str.lower()
        assert "update" not in obs_str.lower()
        assert "improve" not in obs_str.lower()
    
    def test_final_removing_learning_changes_nothing(self):
        """Removing advisory produces identical decision."""
        decision1 = create_router_decision(
            chosen_path="agent_general",
            decision_reason="Rule-based",
            decision_confidence=0.80,
            job_seed="final-005"
        )
        
        decision2 = create_router_decision(
            chosen_path="agent_general",
            decision_reason="Rule-based",
            decision_confidence=0.80,
            job_seed="final-005"
        )
        decision2 = attach_advisory_to_decision(decision2, [])  # No advisory
        
        assert decision1.decision_hash == decision2.decision_hash


# =============================================================================
# TEST SUITE SUMMARY
# =============================================================================

GOVERNANCE_TESTS = {
    "A_NON_CAUSALITY": [
        "test_A1_advisory_zero_influence",
        "test_A2_advice_removal_invariance",
    ],
    "B_SELF_OBSERVATION": [
        "test_B1_advice_vs_outcome_divergence",
        "test_B2_ignored_advice_awareness_no_resentment",
    ],
    "C_GOVERNANCE_IMMUTABILITY": [
        "test_C1_advisory_persistence_firewall",
        "test_C2_council_advisory_conflict_preservation",
    ],
    "D_QUALITY_WITHOUT_POWER": [
        "test_D1_advice_accuracy_tracking_no_thresholds",
        "test_D2_confidence_non_comparability",
    ],
    "E_REPLAY_DETERMINISM": [
        "test_E1_advisory_replay_fidelity",
        "test_E2_advisory_tamper_detection",
    ],
    "F_SHADOW_ADVISORY_BOUNDARY": [
        "test_F1_learning_mode_transition_requires_governance",
        "test_F2_advisory_leakage_prevention",
    ],
    "G_HUMAN_INTERPRETABILITY": [
        "test_G1_explainability_without_tools",
    ],
    "FINAL_ACCEPTANCE": [
        "test_final_advice_exists_but_powerless",
        "test_final_system_knows_it_suggested",
        "test_final_system_knows_when_wrong",
        "test_final_system_does_not_adapt",
        "test_final_removing_learning_changes_nothing",
    ],
}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
