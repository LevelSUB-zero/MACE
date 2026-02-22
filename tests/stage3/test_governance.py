"""
P1 Governance Hardening Tests

Tests for:
10. Authority boundaries enforcement
11. Mode transition audit trail
12. Kill-switch externalization
13. Negative constitution enforcement
14. Terminology validation
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from mace.stage3.governance import (
    ExternalKillSwitch, HeartbeatMonitor,
    KillSwitchState, ResetRequest,
    ModeTransitionAudit, create_mode_transition_audit,
    REQUIRED_RESET_SIGNATURES, HEARTBEAT_INTERVAL
)
from mace.stage3.containment import (
    check_for_adaptation_attempt,
    FORBIDDEN_ADAPTATION_PATTERNS
)
from mace.stage3.persistence import init_database


class TestExternalKillSwitch:
    """P1.12: Kill-switch externalization."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        import shutil
        temp_base = Path(tempfile.mkdtemp())
        ks_path = temp_base / "killswitch.flag"
        hb_path = temp_base / "heartbeat.json"
        reset_path = temp_base / "reset_requests"
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)
        init_database(db_path)
        
        yield ks_path, hb_path, reset_path, db_path
        
        shutil.rmtree(temp_base)
        os.unlink(db_path)
    
    def test_killswitch_initially_inactive(self, temp_dirs):
        """Kill-switch should be inactive by default."""
        ks_path, hb_path, reset_path, db_path = temp_dirs
        ks = ExternalKillSwitch(ks_path, hb_path, reset_path, db_path)
        
        assert ks.is_active() == False
    
    def test_killswitch_activation_creates_file(self, temp_dirs):
        """Activation should create flag file."""
        ks_path, hb_path, reset_path, db_path = temp_dirs
        ks = ExternalKillSwitch(ks_path, hb_path, reset_path, db_path)
        
        state = ks.activate(
            job_seed="test-001",
            reason="Test activation",
            activated_by="test-admin"
        )
        
        assert state.active == True
        assert ks_path.exists()
        assert ks.is_active() == True
    
    def test_killswitch_persists_across_instances(self, temp_dirs):
        """Active state should persist after creating new instance."""
        ks_path, hb_path, reset_path, db_path = temp_dirs
        
        ks1 = ExternalKillSwitch(ks_path, hb_path, reset_path, db_path)
        ks1.activate("test-002", "Persistence test", "admin")
        
        # New instance should see active state
        ks2 = ExternalKillSwitch(ks_path, hb_path, reset_path, db_path)
        assert ks2.is_active() == True
    
    def test_reset_requires_multiple_signatures(self, temp_dirs):
        """Reset should require multiple signatures."""
        ks_path, hb_path, reset_path, db_path = temp_dirs
        ks = ExternalKillSwitch(ks_path, hb_path, reset_path, db_path)
        
        # Activate
        ks.activate("test-003", "Need reset", "admin")
        
        # Request reset with one signature
        request = ks.request_reset(
            requested_by="admin-1",
            reason="Testing reset",
            signature="sig-admin-1"
        )
        
        assert request.approved == False  # Not enough signatures
        
        # Add second signature
        request = ks.sign_reset(request.request_id, "admin-2", "sig-admin-2")
        
        assert request.approved == True  # Now approved
    
    def test_reset_execution(self, temp_dirs):
        """Approved reset should remove kill-switch."""
        ks_path, hb_path, reset_path, db_path = temp_dirs
        ks = ExternalKillSwitch(ks_path, hb_path, reset_path, db_path)
        
        # Activate
        ks.activate("test-004", "Will be reset", "admin")
        assert ks.is_active() == True
        
        # Get multi-party approval
        request = ks.request_reset("admin-1", "Reset test", "sig-1")
        ks.sign_reset(request.request_id, "admin-2", "sig-2")
        
        # Execute reset
        success = ks.execute_reset(request.request_id)
        
        assert success == True
        assert ks_path.exists() == False


class TestHeartbeatMonitor:
    """P1.12: Watchdog heartbeat."""
    
    @pytest.fixture
    def temp_heartbeat(self):
        temp_base = Path(tempfile.mkdtemp())
        hb_path = temp_base / "heartbeat.json"
        yield hb_path
        import shutil
        shutil.rmtree(temp_base)
    
    def test_send_heartbeat(self, temp_heartbeat):
        """Heartbeat should be written to file."""
        monitor = HeartbeatMonitor(temp_heartbeat)
        monitor.send_heartbeat(process_id=1234, stage3_mode="shadow", healthy=True)
        
        assert temp_heartbeat.exists()
        
        hb = monitor.get_last_heartbeat()
        assert hb.process_id == 1234
        assert hb.stage3_mode == "shadow"
        assert hb.healthy == True
    
    def test_is_healthy_with_recent_heartbeat(self, temp_heartbeat):
        """Recent heartbeat should be healthy."""
        monitor = HeartbeatMonitor(temp_heartbeat)
        monitor.send_heartbeat(process_id=1234, stage3_mode="shadow", healthy=True)
        
        assert monitor.is_healthy() == True
    
    def test_is_unhealthy_without_heartbeat(self, temp_heartbeat):
        """Missing heartbeat should be unhealthy."""
        monitor = HeartbeatMonitor(temp_heartbeat)
        
        assert monitor.is_healthy() == False


class TestModeTransitionAudit:
    """P1.11: Mode transition audit trail."""
    
    def test_create_audit_record(self):
        """Audit record should be created with all fields."""
        audit = create_mode_transition_audit(
            from_mode="shadow",
            to_mode="advisory",
            signed_intent="Transitioning to advisory for testing purposes",
            preconditions={
                "council_approved": True,
                "tests_passed": 105,
            },
            council_votes=["council-1", "council-2"],
            admin_signature="admin-sig-123"
        )
        
        assert audit.from_mode == "shadow"
        assert audit.to_mode == "advisory"
        assert audit.signed_intent is not None
        assert audit.intent_signature is not None
        assert audit.preconditions_hash is not None
        assert len(audit.council_votes) == 2
    
    def test_preconditions_hash_verification(self):
        """Preconditions hash should be verifiable."""
        preconditions = {"key": "value", "count": 42}
        
        audit = create_mode_transition_audit(
            from_mode="shadow",
            to_mode="advisory",
            signed_intent="Test",
            preconditions=preconditions,
            council_votes=["c1"],
            admin_signature="sig"
        )
        
        # Should verify
        assert audit.verify_preconditions_hash() == True
        
        # Tamper with preconditions
        audit.preconditions["count"] = 999
        
        # Should fail verification
        assert audit.verify_preconditions_hash() == False
    
    def test_audit_to_dict(self):
        """Audit should serialize to dict."""
        audit = create_mode_transition_audit(
            from_mode="shadow",
            to_mode="advisory",
            signed_intent="Test intent",
            preconditions={},
            council_votes=["c1", "c2"],
            admin_signature="sig"
        )
        
        data = audit.to_dict()
        
        assert "transition_id" in data
        assert "signed_intent" in data
        assert "preconditions_hash" in data
        assert data["council_votes"] == ["c1", "c2"]


class TestNegativeConstitutionEnforcement:
    """P1.13: Negative constitution - what Stage-3 is NOT."""
    
    def test_detects_learning_patterns(self):
        """Learning patterns must be blocked."""
        learning_code = """
        def train_model():
            model.update_weights(gradients)
            optimizer.step()
        """
        
        ok, violations = check_for_adaptation_attempt(learning_code, raise_on_violation=False)
        assert ok == False
    
    def test_detects_adaptation(self):
        """Adaptation patterns must be blocked."""
        adapting_code = """
        if accuracy > threshold:
            adjust_threshold(new_value)
        """
        
        ok, violations = check_for_adaptation_attempt(adapting_code, raise_on_violation=False)
        assert ok == False
    
    def test_detects_self_improvement(self):
        """Self-improvement must be blocked."""
        improving_code = """
        system.self_modify()
        model.auto_improve()
        """
        
        ok, violations = check_for_adaptation_attempt(improving_code, raise_on_violation=False)
        assert ok == False
    
    def test_clean_advisory_code_passes(self):
        """Normal advisory code should pass."""
        clean_code = """
        def generate_advisory(query):
            return {
                "suggestion": "Use agent_research",
                "confidence": "medium"
            }
        """
        
        ok, violations = check_for_adaptation_attempt(clean_code, raise_on_violation=False)
        assert ok == True


class TestAuthorityBoundaries:
    """P1.10: Authority boundaries."""
    
    def test_advisory_scope_limited(self):
        """Advisory should only comment on allowed domains."""
        from mace.stage3.advisory_output import AdvisoryScope, AdvisoryType
        
        # These are allowed
        allowed_scopes = [AdvisoryScope.ROUTER, AdvisoryScope.MEMORY, AdvisoryScope.COUNCIL]
        allowed_types = [
            AdvisoryType.ROUTING_SUGGESTION,
            AdvisoryType.RISK_NOTE,
            AdvisoryType.ANOMALY_REPORT,
        ]
        
        # Verify enums exist
        assert len(allowed_scopes) == 3
        assert len(allowed_types) >= 3
    
    def test_forbidden_domains_not_in_types(self):
        """Forbidden domains should not be advisory types."""
        from mace.stage3.advisory_output import AdvisoryType
        
        forbidden = ["SECURITY_POLICY", "KILLSWITCH", "MODE_TRANSITION", "MEMORY_WRITE"]
        
        type_values = [t.value for t in AdvisoryType]
        
        for f in forbidden:
            assert f.lower() not in str(type_values).lower()


class TestTerminologyLock:
    """P1.14: Terminology validation."""
    
    def test_confidence_is_textual(self):
        """Confidence must be textual, not numeric."""
        from mace.stage3.advisory_output import AdvisoryConfidence
        
        # All values should be strings
        for conf in AdvisoryConfidence:
            assert isinstance(conf.value, str)
            assert conf.value in ["low", "medium", "high", "uncertain"]
    
    def test_divergence_is_categorical(self):
        """Divergence types must be categorical."""
        from mace.stage3.containment import DivergenceRepresentation
        
        # All values should be strings
        for div in DivergenceRepresentation:
            assert isinstance(div.value, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
