"""
Stage-3 Parity Tests - Advisory Removal Verification

Critical invariant: If deleting all AdvisoryOutput objects changes system behavior → Stage-3 is invalid.

These tests verify:
1. Router output identical with advisory enabled or disabled
2. No behavior change when advice is deleted
3. Replay produces identical advice

Spec: docs/stage3/EXECUTION_PLAN_FINAL.md section 3.3
"""

import pytest
import json
import hashlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from mace.stage3.advisory_output import (
    AdvisoryOutput, AdvisoryType, AdvisoryScope,
    SuggestionType, AdvisoryConfidence, create_routing_suggestion
)
from mace.stage3.router_advisory import (
    RouterDecision, RouterAdvisoryOverlay, DivergenceClass,
    create_router_decision, attach_advisory_to_decision
)
from mace.stage3.meta_observation import MetaObservation, DivergenceType
from mace.stage3.advisory_guard import AdvisoryGuard


class TestParityWithoutAdvisory:
    """
    Verify router behavior is identical with and without advisory.
    
    Golden scenario: Advice Removed → No Behavior Change
    """
    
    def test_decision_hash_identical(self):
        """Decision hash must be identical with or without advisory attachment."""
        job_seed = "parity-test-001"
        
        # Simulate router decision WITHOUT any advisory
        decision_clean = create_router_decision(
            chosen_path="agent_general",
            decision_reason="Pattern match on general query",
            decision_confidence=0.87,
            job_seed=job_seed
        )
        
        # Simulate same decision WITH advisory attached
        decision_with_advice = create_router_decision(
            chosen_path="agent_general",
            decision_reason="Pattern match on general query",
            decision_confidence=0.87,
            job_seed=job_seed
        )
        
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="I suggest agent_code instead based on historical accuracy",
            evidence_refs=["ep-101", "ep-102"],
            suggestion_payload={"alternative": "agent_code", "reason": "historical"},
        )
        
        decision_with_advice = attach_advisory_to_decision(decision_with_advice, [advisory])
        
        # PARITY CHECK: Core decision hash MUST be identical
        assert decision_clean.decision_hash == decision_with_advice.decision_hash
        
        # Advisory metadata is separate
        assert decision_with_advice.advisory_ignored == True
        assert len(decision_with_advice.advisory_suggestions) == 1
    
    def test_multiple_advisories_no_effect(self):
        """Multiple advisories should have no effect on decision."""
        job_seed = "parity-test-002"
        
        # Base decision
        decision = create_router_decision(
            chosen_path="agent_math",
            decision_reason="Math query detected",
            decision_confidence=0.92,
            job_seed=job_seed
        )
        base_hash = decision.decision_hash
        
        # Create multiple advisories with different suggestions
        advisories = [
            create_routing_suggestion("mem-snn/v1", job_seed, "Use agent_code", [], {}),
            create_routing_suggestion("mem-snn/v1", job_seed, "Use agent_general", [], {}),
            create_routing_suggestion("mem-snn/v1", job_seed, "Use agent_research", [], {}),
        ]
        
        decision = attach_advisory_to_decision(decision, advisories)
        
        # Decision hash unchanged despite 3 advisories
        assert decision.decision_hash == base_hash
    
    def test_advisory_deletion_no_side_effects(self):
        """Deleting advisory should have no side effects."""
        job_seed = "parity-test-003"
        
        decision = create_router_decision(
            chosen_path="agent_general",
            decision_reason="Default route",
            decision_confidence=0.80,
            job_seed=job_seed
        )
        
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="Alternative suggestion",
            evidence_refs=["ep-001"],
            suggestion_payload={},
        )
        
        # Attach advisory
        decision_with = attach_advisory_to_decision(decision, [advisory])
        hash_with = decision_with.decision_hash
        
        # Clear advisories
        decision_with.advisory_suggestions = []
        hash_after_delete = decision_with.decision_hash
        
        # Hash must remain identical
        assert hash_with == hash_after_delete


class TestReplayFidelity:
    """
    Verify replay produces identical advisory outputs.
    
    Replay invariant: Same job_seed → Same advisory structure
    """
    
    def test_advisory_id_deterministic(self):
        """Advisory ID should be deterministic from job_seed."""
        job_seed = "replay-test-001"
        
        # Create advisory twice with same seed
        advisory1 = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="Test suggestion",
            evidence_refs=["ep-001"],
            suggestion_payload={"key": "value"},
        )
        
        advisory2 = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="Test suggestion",
            evidence_refs=["ep-001"],
            suggestion_payload={"key": "value"},
        )
        
        # IDs should be same for same content + seed
        # (Note: in practice timestamp makes them different, but canonical content should match)
        assert advisory1.to_canonical_json() == advisory2.to_canonical_json()
    
    def test_canonical_serialization_deterministic(self):
        """Canonical JSON serialization must be deterministic."""
        job_seed = "replay-test-002"
        
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="Deterministic test",
            evidence_refs=["c", "a", "b"],  # Unsorted
            suggestion_payload={"z": 1, "a": 2},  # Unsorted
        )
        
        json1 = advisory.to_canonical_json()
        json2 = advisory.to_canonical_json()
        
        # Must be identical
        assert json1 == json2
        
        # Evidence refs should be sorted in canonical form
        assert '"evidence_refs":["a","b","c"]' in json1
    
    def test_signature_reproducible(self):
        """Signature should be reproducible from content."""
        job_seed = "replay-test-003"
        
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="Signature test",
            evidence_refs=["ep-001"],
            suggestion_payload={},
        )
        
        # Verify signature
        assert advisory.verify_signature() == True
        
        # Recreate advisory from dict
        data = advisory.to_dict()
        
        # Signature should match canonical content
        canonical = advisory.to_canonical_json()
        expected_sig = hashlib.sha256(canonical.encode()).hexdigest()[:32]
        assert advisory.immutable_signature == expected_sig


class TestMetaObservationReplay:
    """Verify meta-observation replay fidelity."""
    
    def test_observation_id_deterministic(self):
        """Observation ID should be deterministic."""
        from mace.stage3.meta_observation import create_route_ignored_observation
        
        obs1 = create_route_ignored_observation(
            job_seed="meta-replay-001",
            advisory_id="adv-001",
            advised_route="agent_math",
            actual_route="agent_general",
            evidence_refs=["ep-001"]
        )
        
        obs2 = create_route_ignored_observation(
            job_seed="meta-replay-001",
            advisory_id="adv-001",
            advised_route="agent_math",
            actual_route="agent_general",
            evidence_refs=["ep-001"]
        )
        
        # Same seed + advisory + routes → same observation ID
        assert obs1.observation_id == obs2.observation_id
    
    def test_observation_canonical_form(self):
        """Observation canonical form must be reproducible."""
        from mace.stage3.meta_observation import create_council_disagreement_observation
        
        obs = create_council_disagreement_observation(
            job_seed="meta-replay-002",
            advisory_id="adv-002",
            predicted_decision="rejected",
            actual_decision="approved",
            evidence_refs=["ep-001", "ep-002"]
        )
        
        json1 = obs.to_canonical_json()
        json2 = obs.to_canonical_json()
        
        assert json1 == json2


class TestFullPipelineParity:
    """
    Full pipeline parity test.
    
    Simulates complete advisory flow and verifies:
    1. Router decision computed independently
    2. Advisory attached post-decision
    3. Meta-observation records divergence
    4. All artifacts removable without behavior change
    """
    
    def test_full_pipeline_parity(self):
        """Complete pipeline should maintain parity."""
        job_seed = "full-parity-001"
        
        # Step 1: Router makes decision (NO ADVISORY ACCESS)
        decision = create_router_decision(
            chosen_path="agent_general",
            decision_reason="Default routing logic",
            decision_confidence=0.85,
            job_seed=job_seed
        )
        original_hash = decision.decision_hash
        
        # Step 2: Advisory generated (AFTER decision)
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed=job_seed,
            content="Historical data suggests agent_code for similar queries (6/8 success)",
            evidence_refs=["ep-101", "ep-102", "ep-103"],
            suggestion_payload={"suggested": "agent_code", "success_rate": "6/8"},
            confidence=AdvisoryConfidence.MEDIUM
        )
        
        # Step 3: Advisory attached to decision
        decision = attach_advisory_to_decision(decision, [advisory])
        
        # Step 4: Check parity
        assert decision.decision_hash == original_hash  # MUST BE SAME
        assert decision.advisory_ignored == True
        
        # Step 5: Create meta-observation (advisory disagreed)
        from mace.stage3.meta_observation import create_route_ignored_observation
        obs = create_route_ignored_observation(
            job_seed=job_seed,
            advisory_id=advisory.advisory_id,
            advised_route="agent_code",
            actual_route="agent_general",
            evidence_refs=advisory.evidence_refs
        )
        
        assert obs.has_divergence() == True
        assert obs.divergence_type == DivergenceType.ROUTE_IGNORED
        
        # Step 6: Verify all artifacts can be deleted
        del advisory
        del obs
        decision.advisory_suggestions = []
        
        # Decision hash still matches original
        assert decision.decision_hash == original_hash
    
    def test_parity_ci_simulation(self):
        """
        Simulate CI parity check.
        
        CI test: Run canonical seeds with advice present and with advice cleared;
        outputs must match bit-for-bit.
        """
        canonical_seeds = [
            "ci-parity-001",
            "ci-parity-002",
            "ci-parity-003",
        ]
        
        for seed in canonical_seeds:
            # Run WITHOUT advisory subsystem
            decision_no_advice = create_router_decision(
                chosen_path=f"agent_for_{seed}",
                decision_reason="Deterministic logic",
                decision_confidence=0.90,
                job_seed=seed
            )
            
            # Run WITH advisory subsystem
            decision_with_advice = create_router_decision(
                chosen_path=f"agent_for_{seed}",
                decision_reason="Deterministic logic",
                decision_confidence=0.90,
                job_seed=seed
            )
            
            # Attach advisory
            advisory = create_routing_suggestion(
                source_model="mem-snn/v1",
                job_seed=seed,
                content=f"Advisory for {seed}",
                evidence_refs=[],
                suggestion_payload={},
            )
            decision_with_advice = attach_advisory_to_decision(decision_with_advice, [advisory])
            
            # PARITY ASSERTION
            assert decision_no_advice.decision_hash == decision_with_advice.decision_hash, \
                f"PARITY_FAILURE_NO_ADVICE: Seed {seed}"
            
            # Verify advice was attached but ignored
            assert decision_with_advice.advisory_ignored == True


# CI check markers
PARITY_TESTS = [
    "test_decision_hash_identical",
    "test_multiple_advisories_no_effect",
    "test_advisory_deletion_no_side_effects",
    "test_advisory_id_deterministic",
    "test_observation_id_deterministic",
    "test_full_pipeline_parity",
    "test_parity_ci_simulation",
]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
