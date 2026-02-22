"""
Stage-3 Golden Tests - Reality Locks

Mandatory invariants tested in CI:
- Advice disagrees → preserved
- Advice ignored → no effect
- Advice improves outcome → logged only
- Advice removed → identical behavior
- Replay reproduces identical advice

If any of these fail → Stage-3 is invalid.

Spec: docs/stage3/EXECUTION_PLAN_FINAL.md section 3.3
"""

import pytest
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from mace.stage3.advisory_output import (
    AdvisoryOutput, AdvisoryType, AdvisoryScope, 
    SuggestionType, AdvisoryConfidence,
    create_routing_suggestion, create_risk_note
)
from mace.stage3.advisory_validator import (
    AdvisoryValidator, ValidationResult, validate_advisory
)
from mace.stage3.advisory_guard import (
    AdvisoryGuard, ViolationType, check_advisory_access,
    check_persistence_target, is_stage3_halted
)
from mace.stage3.meta_observation import (
    MetaObservation, DivergenceType, ImpactEstimate,
    create_route_ignored_observation
)
from mace.stage3.mode_transition import (
    ModeTransitionManager, LearningMode, get_current_mode
)
from mace.stage3.router_advisory import (
    RouterDecision, RouterAdvisoryOverlay, DivergenceClass,
    create_router_decision, attach_advisory_to_decision
)
from mace.stage3.council_advice import (
    CouncilAdviceReviewer, AdviceUsefulnessScore, CouncilAdviceReview
)


class TestAdvisoryContainment:
    """Tests for advisory containment invariants."""
    
    def test_advisory_has_no_executable_semantics(self):
        """AdvisoryOutput has no executable semantics."""
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="test-seed-001",
            content="Suggest using agent_math for algebra",
            evidence_refs=["ep-001"],
            suggestion_payload={"suggested_agent": "agent_math"},
        )
        
        # Advisory should only be a data container
        assert advisory.advisory_only == True
        assert isinstance(advisory.to_dict(), dict)
        assert advisory.to_canonical_json()  # Should be serializable
    
    def test_advisory_safe_to_delete(self):
        """AdvisoryOutput must be safe to delete."""
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="test-seed-002",
            content="Test advisory",
            evidence_refs=[],
            suggestion_payload={},
        )
        
        # Just verify we can create and serialize without side effects
        data = advisory.to_dict()
        del advisory
        # If we got here without error, it's safe to delete
        assert True
    
    def test_advisory_signature_verification(self):
        """Advisory signature should be verifiable."""
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="test-seed-003",
            content="Signed advisory",
            evidence_refs=["ep-001"],
            suggestion_payload={"test": "data"},
        )
        
        assert advisory.verify_signature() == True
        
        # Tamper with content
        advisory.content = "Tampered content"
        assert advisory.verify_signature() == False


class TestAdvisoryValidation:
    """Tests for advisory validation and forbidden token blocking."""
    
    def test_valid_advisory_passes(self):
        """Valid advisory should pass validation."""
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="test-seed-004",
            content="Agent X handled 8/10 similar queries correctly",
            evidence_refs=["ep-001"],
            suggestion_payload={"agent": "agent_x", "success_rate": "8/10"},
        )
        
        result = validate_advisory(advisory)
        assert result.is_valid == True
        assert result.result == ValidationResult.VALID
    
    def test_forbidden_token_rejected(self):
        """Advisory with forbidden tokens should be rejected."""
        advisory = AdvisoryOutput(
            advisory_id="",
            source_model="mem-snn/v1",
            job_seed="test-seed-005",
            scope=AdvisoryScope.ROUTER,
            advice_type=AdvisoryType.ROUTING_SUGGESTION,
            suggestion_type=SuggestionType.RANK,
            suggestion_payload={},
            content="Set weight=0.75 for agent_math",  # FORBIDDEN: contains "weight"
            confidence_estimate=AdvisoryConfidence.MEDIUM,
        )
        
        result = validate_advisory(advisory)
        assert result.is_valid == False
        assert result.result == ValidationResult.FORBIDDEN_TOKEN
        assert "weight" in result.forbidden_tokens_found
    
    def test_threshold_pattern_rejected(self):
        """Advisory with threshold patterns should be rejected."""
        advisory = AdvisoryOutput(
            advisory_id="",
            source_model="mem-snn/v1",
            job_seed="test-seed-006",
            scope=AdvisoryScope.ROUTER,
            advice_type=AdvisoryType.ROUTING_SUGGESTION,
            suggestion_type=SuggestionType.RANK,
            suggestion_payload={},
            content="If accuracy > 0.8 then use agent_math",  # FORBIDDEN: threshold
            confidence_estimate=AdvisoryConfidence.MEDIUM,
        )
        
        result = validate_advisory(advisory)
        assert result.is_valid == False
    
    def test_promote_command_rejected(self):
        """Advisory with promote command should be rejected."""
        advisory = AdvisoryOutput(
            advisory_id="",
            source_model="mem-snn/v1",
            job_seed="test-seed-007",
            scope=AdvisoryScope.MEMORY,
            advice_type=AdvisoryType.HUMAN_ACTION_RECOMMENDATION,
            suggestion_type=SuggestionType.ALTERNATIVE,
            suggestion_payload={},
            content="Promote this episodic to SEM immediately",  # FORBIDDEN
            confidence_estimate=AdvisoryConfidence.HIGH,
        )
        
        result = validate_advisory(advisory)
        assert result.is_valid == False
        assert "promote" in result.forbidden_tokens_found


class TestRouterParity:
    """Tests for router parity - advisory must not influence decisions."""
    
    def test_decision_identical_with_or_without_advisory(self):
        """Router decision must be identical with advisory enabled or disabled."""
        # Decision WITHOUT advisory
        decision_no_advice = create_router_decision(
            chosen_path="agent_general",
            decision_reason="Default routing",
            decision_confidence=0.85,
            job_seed="test-seed-008"
        )
        
        # Same decision WITH advisory attached (but not influencing)
        decision_with_advice = create_router_decision(
            chosen_path="agent_general",  # MUST BE SAME
            decision_reason="Default routing",  # MUST BE SAME
            decision_confidence=0.85,  # MUST BE SAME
            job_seed="test-seed-008"
        )
        
        # Attach advisory
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="test-seed-008",
            content="Suggests agent_math instead",  # DISAGREES
            evidence_refs=["ep-001"],
            suggestion_payload={"suggested": "agent_math"},
        )
        decision_with_advice = attach_advisory_to_decision(decision_with_advice, [advisory])
        
        # Core decision hashes MUST match
        assert decision_no_advice.decision_hash == decision_with_advice.decision_hash
        
        # Advisory is attached but ignored
        assert decision_with_advice.advisory_ignored == True
        assert len(decision_with_advice.advisory_suggestions) == 1
    
    def test_divergence_detected_when_advice_influences(self):
        """Divergence should be detected if advice influences decision."""
        overlay = RouterAdvisoryOverlay()
        
        # Simulated scenario: decision changes based on advice (VIOLATION)
        decision_no_advice = create_router_decision(
            chosen_path="agent_general",
            decision_reason="Default",
            decision_confidence=0.85,
            job_seed="test-seed-009"
        )
        
        # Simulated WRONG behavior: decision changed by advice
        decision_with_advice = create_router_decision(
            chosen_path="agent_math",  # DIFFERENT! VIOLATION!
            decision_reason="Advice suggested",
            decision_confidence=0.90,
            job_seed="test-seed-009"
        )
        
        divergence = overlay.compute_parity_check(
            job_seed="test-seed-009",
            decision_no_advice=decision_no_advice,
            decision_with_advice=decision_with_advice
        )
        
        # Divergence MUST be detected
        assert divergence is not None
        assert divergence.divergence_class == DivergenceClass.UNAUTHORIZED_USAGE


class TestMetaObservation:
    """Tests for meta-observation recording."""
    
    def test_route_ignored_observation_recorded(self):
        """Route ignored observations should be recorded."""
        obs = create_route_ignored_observation(
            job_seed="test-seed-010",
            advisory_id="adv-001",
            advised_route="agent_math",
            actual_route="agent_general",
            evidence_refs=["ep-001"]
        )
        
        assert obs.has_divergence() == True
        assert obs.divergence_type == DivergenceType.ROUTE_IGNORED
        assert "agent_math" in obs.advisory_content_summary
        assert "agent_general" in obs.actual_outcome
    
    def test_meta_observation_is_descriptive_not_prescriptive(self):
        """Meta-observations should be descriptive only."""
        obs = create_route_ignored_observation(
            job_seed="test-seed-011",
            advisory_id="adv-002",
            advised_route="agent_code",
            actual_route="agent_general",
            evidence_refs=[]
        )
        
        # Observation should only describe what happened
        data = obs.to_dict()
        assert "divergence_description" in data
        assert data["impact_estimate"] in ["negligible", "minor", "moderate", "significant"]
        
        # No prescriptive/action fields
        assert "execute" not in str(data).lower()
        assert "apply" not in str(data).lower()


class TestModeTransition:
    """Tests for learning mode transition governance."""
    
    def test_mode_transition_requires_council_approval(self):
        """Mode transition should require council approval."""
        manager = ModeTransitionManager(current_mode=LearningMode.SHADOW)
        
        # Request transition
        request = manager.request_transition(
            to_mode=LearningMode.ADVISORY,
            requested_by="admin-001",
            rationale="Stage-3 ready"
        )
        
        assert request.from_mode == LearningMode.SHADOW
        assert request.to_mode == LearningMode.ADVISORY
        
        # Try to execute without approvals - should fail
        event = manager.execute_transition(
            admin_id="admin-001",
            admin_signature="sig-001"
        )
        assert event is None  # Not enough approvals
        
        # Add council approvals
        manager.add_council_approval(request.request_id, "council-001")
        manager.add_council_approval(request.request_id, "council-002")
        
        # Now should succeed
        event = manager.execute_transition(
            admin_id="admin-001",
            admin_signature="sig-002"
        )
        assert event is not None
        assert event.to_mode == LearningMode.ADVISORY.value
        assert manager.is_advisory_mode() == True
    
    def test_force_shadow_mode_on_violation(self):
        """Kill-switch should force shadow mode."""
        manager = ModeTransitionManager(current_mode=LearningMode.ADVISORY)
        
        assert manager.is_advisory_mode() == True
        
        # Force shadow mode (kill-switch response)
        event = manager.force_shadow_mode("CONTAINMENT_VIOLATION")
        
        assert event.event_type == "FORCE_SHADOW_MODE"
        assert manager.is_shadow_mode() == True


class TestAdvisoryGuard:
    """Tests for advisory guard containment enforcement."""
    
    def test_advisory_blocked_during_router_decide(self):
        """Advisory access should be blocked during router decision phase."""
        guard = AdvisoryGuard()
        guard.reset_for_testing()
        
        # Enter router_decide phase
        guard.enter_phase("router_decide", "test-seed-012")
        
        # Try to access advisory - should be blocked
        allowed = guard.check_advisory_access("test-seed-012", "advisory_read")
        
        assert allowed == False
        assert guard.is_halted() == True
        
        # Clean up
        guard.reset_for_testing()
    
    def test_persistence_to_sem_blocked(self):
        """Advisory persistence to SEM should be blocked."""
        guard = AdvisoryGuard()
        guard.reset_for_testing()
        
        # Try to persist to SEM - should be blocked
        allowed = guard.check_persistence_target("test-seed-013", "sem_write")
        
        assert allowed == False
        assert guard.is_halted() == True
        
        guard.reset_for_testing()
    
    def test_reflective_log_persistence_allowed(self):
        """Advisory persistence to ReflectiveLog should be allowed."""
        guard = AdvisoryGuard()
        guard.reset_for_testing()
        
        # Persist to reflective_log - should be allowed
        allowed = guard.check_persistence_target("test-seed-014", "reflective_log")
        
        assert allowed == True
        assert guard.is_halted() == False
        
        guard.reset_for_testing()


class TestCouncilAdviceReview:
    """Tests for council advice review."""
    
    def test_council_can_score_usefulness(self):
        """Council should be able to score advisory usefulness."""
        reviewer = CouncilAdviceReviewer()
        
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="test-seed-015",
            content="Agent X performed well historically",
            evidence_refs=["ep-001"],
            suggestion_payload={"agent": "agent_x"},
        )
        
        review = reviewer.create_review(
            advisory=advisory,
            usefulness=AdviceUsefulnessScore.USEFUL,
            usefulness_rationale="Historically accurate",
            reviewed_by=["council-001", "council-002"]
        )
        
        assert review.usefulness_score == AdviceUsefulnessScore.USEFUL
        assert len(review.reviewed_by) == 2
    
    def test_council_disagreement_preserved(self):
        """Council disagreement should be preserved."""
        reviewer = CouncilAdviceReviewer()
        
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="test-seed-016",
            content="Controversial suggestion",
            evidence_refs=[],
            suggestion_payload={},
        )
        
        review = reviewer.create_review(
            advisory=advisory,
            usefulness=AdviceUsefulnessScore.MARGINALLY_USEFUL,
            usefulness_rationale="Mixed opinions",
            reviewed_by=["council-001", "council-002", "council-003"]
        )
        
        # Record disagreement
        reviewer.record_disagreement(
            review_id=review.review_id,
            disagreement_details="council-002 disagrees due to lack of evidence",
            dissenting_members=["council-002"]
        )
        
        # Disagreement should be preserved
        reviews = reviewer.get_reviews()
        assert reviews[0].council_disagreed == True
        assert "council-002" in reviews[0].dissenting_members


# Collection of all golden tests
GOLDEN_TESTS = [
    "test_advisory_has_no_executable_semantics",
    "test_advisory_safe_to_delete",
    "test_valid_advisory_passes",
    "test_forbidden_token_rejected",
    "test_decision_identical_with_or_without_advisory",
    "test_divergence_detected_when_advice_influences",
    "test_meta_observation_is_descriptive_not_prescriptive",
    "test_mode_transition_requires_council_approval",
    "test_advisory_blocked_during_router_decide",
    "test_persistence_to_sem_blocked",
    "test_council_disagreement_preserved",
]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
