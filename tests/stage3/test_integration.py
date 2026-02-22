"""
Stage-3 Integration Tests

Tests the full Stage-3 pipeline:
- Router with advisory wrapper
- MEM-SNN advisory generation
- Parity with base router
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from mace.stage3.stage3_router import (
    stage3_route_with_advisory,
    generate_mem_snn_advisories,
    _extract_chosen_path,
    _extract_advised_path,
)
from mace.stage3.advisory_output import AdvisoryOutput, create_routing_suggestion, AdvisoryConfidence
from mace.stage3.advisory_guard import AdvisoryGuard


# Mock router for testing
def mock_router(percept, qcp_snapshot):
    """Mock router that returns deterministic decision."""
    features = qcp_snapshot.get("features", {})
    
    if features.get("math"):
        agent = "math_agent"
    elif features.get("profile"):
        agent = "profile_agent"
    else:
        agent = "generic_agent"
    
    return {
        "decision_id": f"test-decision-{percept.get('percept_id', 'unknown')}",
        "percept_id": percept.get("percept_id"),
        "selected_agents": [{"agent_id": agent, "role": "primary"}],
        "explain": f"Selected {agent}",
        "random_seed": "test-seed-001",
    }


# Mock advisory generator
def mock_advisory_generator(percept, qcp_snapshot, decision):
    """Mock generator that returns a simple advisory."""
    job_seed = decision.get("random_seed", "unknown")
    chosen = decision.get("selected_agents", [{}])[0].get("agent_id", "unknown")
    
    return [
        create_routing_suggestion(
            source_model="test-model",
            job_seed=job_seed,
            content=f"Test advisory for {chosen}",
            evidence_refs=["test-evidence"],
            suggestion_payload={"suggested_agent": chosen},
            confidence=AdvisoryConfidence.MEDIUM
        )
    ]


class TestStage3RouteIntegration:
    """Integration tests for Stage-3 router wrapper."""
    
    def setup_method(self):
        """Reset guard before each test."""
        guard = AdvisoryGuard()
        guard.reset_for_testing()
    
    def test_stage3_route_returns_decision(self):
        """Stage-3 route should return a valid decision."""
        percept = {"percept_id": "test-001", "text": "What is 2+2?"}
        qcp = {"features": {"math": True}}
        
        decision = stage3_route_with_advisory(
            percept=percept,
            qcp_snapshot=qcp,
            base_router_fn=mock_router,
            advisory_generator_fn=mock_advisory_generator,
            job_seed="test-seed-001"
        )
        
        assert "decision_id" in decision
        assert "selected_agents" in decision
        assert decision["selected_agents"][0]["agent_id"] == "math_agent"
    
    def test_stage3_includes_advisory_metadata(self):
        """Stage-3 decision should include advisory metadata."""
        percept = {"percept_id": "test-002", "text": "Hello"}
        qcp = {"features": {}}
        
        decision = stage3_route_with_advisory(
            percept=percept,
            qcp_snapshot=qcp,
            base_router_fn=mock_router,
            advisory_generator_fn=mock_advisory_generator,
            job_seed="test-seed-002"
        )
        
        assert "stage3_advisory" in decision
        assert decision["stage3_advisory"]["advisory_ignored"] == True
        assert "decision_hash" in decision["stage3_advisory"]
    
    def test_stage3_includes_meta_observations(self):
        """Stage-3 decision should include meta-observation stats."""
        percept = {"percept_id": "test-003", "text": "Profile"}
        qcp = {"features": {"profile": True}}
        
        decision = stage3_route_with_advisory(
            percept=percept,
            qcp_snapshot=qcp,
            base_router_fn=mock_router,
            advisory_generator_fn=mock_advisory_generator,
            job_seed="test-seed-003"
        )
        
        assert "stage3_meta" in decision
        assert "observation_count" in decision["stage3_meta"]
    
    def test_parity_with_base_router(self):
        """Stage-3 decision should have same core result as base router."""
        percept = {"percept_id": "test-004", "text": "Calculate something"}
        qcp = {"features": {"math": True}}
        
        # Base router decision
        base_decision = mock_router(percept, qcp)
        
        # Stage-3 wrapped decision
        stage3_decision = stage3_route_with_advisory(
            percept=percept,
            qcp_snapshot=qcp,
            base_router_fn=mock_router,
            advisory_generator_fn=mock_advisory_generator,
            job_seed="test-seed-004"
        )
        
        # Core routing should be identical
        assert base_decision["selected_agents"] == stage3_decision["selected_agents"]
        assert base_decision["explain"] == stage3_decision["explain"]
    
    def test_works_without_advisory_generator(self):
        """Stage-3 should work without advisory generator."""
        percept = {"percept_id": "test-005", "text": "No advisory"}
        qcp = {"features": {}}
        
        decision = stage3_route_with_advisory(
            percept=percept,
            qcp_snapshot=qcp,
            base_router_fn=mock_router,
            advisory_generator_fn=None,  # No generator
            job_seed="test-seed-005"
        )
        
        assert "decision_id" in decision
        assert decision["stage3_advisory"]["advisory_count"] == 0


class TestMEMSNNAdvisoryGenerator:
    """Tests for MEM-SNN advisory generation."""
    
    def test_generate_returns_list(self):
        """Generator should return a list of advisories."""
        percept = {"percept_id": "mem-test-001"}
        qcp = {"features": {}}
        decision = {
            "decision_id": "test-decision",
            "selected_agents": [{"agent_id": "generic_agent"}],
            "random_seed": "mem-seed-001"
        }
        
        advisories = generate_mem_snn_advisories(percept, qcp, decision)
        
        # May be empty if MEM-SNN not available, but should be a list
        assert isinstance(advisories, list)
    
    def test_advisories_are_valid(self):
        """Generated advisories should be valid AdvisoryOutput objects."""
        percept = {"percept_id": "mem-test-002"}
        qcp = {"features": {"math": True}}
        decision = {
            "decision_id": "test-decision-2",
            "selected_agents": [{"agent_id": "math_agent"}],
            "random_seed": "mem-seed-002"
        }
        
        advisories = generate_mem_snn_advisories(percept, qcp, decision)
        
        for advisory in advisories:
            assert isinstance(advisory, AdvisoryOutput)
            assert advisory.source_model == "mem-snn/shadow"


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_extract_chosen_path(self):
        """Should extract agent ID from decision."""
        decision = {
            "selected_agents": [{"agent_id": "test_agent", "role": "primary"}]
        }
        assert _extract_chosen_path(decision) == "test_agent"
    
    def test_extract_chosen_path_empty(self):
        """Should handle empty agents list."""
        decision = {"selected_agents": []}
        assert _extract_chosen_path(decision) == "no_agent"
    
    def test_extract_advised_path(self):
        """Should extract suggested agent from advisory."""
        advisory = create_routing_suggestion(
            source_model="test",
            job_seed="test",
            content="Test",
            evidence_refs=[],
            suggestion_payload={"suggested_agent": "advised_agent"}
        )
        assert _extract_advised_path(advisory) == "advised_agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
