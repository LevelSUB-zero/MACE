"""
P0 Persistence Tests - Hard Stability Verification

Tests for:
1. Durable ReflectiveLog
2. Persisted Guard State
3. Advisory Generator Versioning
4. Replay Fidelity
"""

import pytest
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from mace.stage3.persistence import (
    init_database, get_connection,
    persist_to_reflective_log, get_reflective_log_entries,
    set_guard_state, get_guard_state, is_killswitch_active, activate_killswitch,
    get_current_learning_mode, set_learning_mode,
    record_violation, get_violations, count_violations,
    persist_advisory_output, get_advisory_by_id, verify_advisory_replay,
    persist_meta_observation, get_divergence_stats,
    log_replay_divergence, verify_replay_fidelity,
    AdvisoryVersion
)
from mace.stage3.advisory_output import (
    create_routing_suggestion, AdvisoryConfidence
)


class TestDurableReflectiveLog:
    """P0 Item 1: Durable ReflectiveLog with crash consistency."""
    
    @pytest.fixture
    def db_path(self):
        """Create temporary database."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_database(path)
        yield path
        os.unlink(path)
    
    def test_reflective_log_persists(self, db_path):
        """Log entries survive database reconnection."""
        # Insert entry
        event_id = persist_to_reflective_log(
            event_type="TEST_EVENT",
            job_seed="persist-test-001",
            payload={"test": "data"},
            decision_hash="abc123",
            db_path=db_path
        )
        
        # Reconnect and verify
        entries = get_reflective_log_entries(
            job_seed="persist-test-001",
            db_path=db_path
        )
        
        assert len(entries) == 1
        assert entries[0]["event_id"] == event_id
        assert entries[0]["schema_version"] == "3.0"
    
    def test_idempotent_insert(self, db_path):
        """Same event inserted twice should not duplicate."""
        payload = {"test": "idempotent"}
        
        event_id_1 = persist_to_reflective_log(
            event_type="IDEM_TEST",
            job_seed="idem-001",
            payload=payload,
            db_path=db_path
        )
        
        event_id_2 = persist_to_reflective_log(
            event_type="IDEM_TEST",
            job_seed="idem-001",
            payload=payload,  # Same payload
            db_path=db_path
        )
        
        # Same event ID (deterministic)
        assert event_id_1 == event_id_2
        
        # Only one entry
        entries = get_reflective_log_entries(job_seed="idem-001", db_path=db_path)
        assert len(entries) == 1
    
    def test_schema_version_in_every_row(self, db_path):
        """Every row must have schema version."""
        persist_to_reflective_log(
            event_type="SCHEMA_TEST",
            job_seed="schema-001",
            payload={},
            db_path=db_path
        )
        
        entries = get_reflective_log_entries(job_seed="schema-001", db_path=db_path)
        assert entries[0]["schema_version"] == "3.0"


class TestPersistedGuardState:
    """P0 Item 2: Guard state persists across restarts."""
    
    @pytest.fixture
    def db_path(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_database(path)
        yield path
        os.unlink(path)
    
    def test_guard_state_persists(self, db_path):
        """Guard state survives reconnection."""
        set_guard_state("test_key", "test_value", db_path)
        
        # Reconnect and verify
        value = get_guard_state("test_key", db_path)
        assert value == "test_value"
    
    def test_killswitch_persists(self, db_path):
        """Kill-switch state persists."""
        assert is_killswitch_active(db_path) == False
        
        activate_killswitch("ks-test-001", "Test activation", db_path)
        
        assert is_killswitch_active(db_path) == True
        assert get_guard_state("killswitch_reason", db_path) == "Test activation"
    
    def test_learning_mode_persists(self, db_path):
        """Learning mode persists."""
        assert get_current_learning_mode(db_path) == "shadow"  # Default
        
        set_learning_mode("advisory", db_path)
        
        assert get_current_learning_mode(db_path) == "advisory"
    
    def test_violations_ledger_persists(self, db_path):
        """Violations are never deleted."""
        record_violation(
            violation_id="viol-001",
            violation_type="TEMPORAL_VIOLATION",
            job_seed="viol-test-001",
            description="Test violation",
            evidence={"test": "data"},
            db_path=db_path
        )
        
        violations = get_violations(db_path=db_path)
        assert len(violations) == 1
        assert violations[0]["violation_type"] == "TEMPORAL_VIOLATION"
        
        # Add another
        record_violation(
            violation_id="viol-002",
            violation_type="PERSISTENCE_VIOLATION",
            job_seed="viol-test-002",
            description="Another violation",
            db_path=db_path
        )
        
        assert count_violations(db_path) == 2


class TestAdvisoryVersioning:
    """P0 Item 3: Advisory generator versioning."""
    
    @pytest.fixture
    def db_path(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_database(path)
        yield path
        os.unlink(path)
    
    def test_advisory_has_versioning_fields(self):
        """Advisory output includes versioning fields."""
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="version-test-001",
            content="Test advisory",
            evidence_refs=[],
            suggestion_payload={},
        )
        
        # Versioning fields exist
        assert hasattr(advisory, 'generator_id')
        assert hasattr(advisory, 'model_version')
        assert hasattr(advisory, 'scoring_method')
        assert hasattr(advisory, 'calibration_version')
        
        # Default values
        assert advisory.generator_id == "mem-snn-shadow-v1"
        assert advisory.scoring_method == "shadow"
    
    def test_advisory_versioning_in_dict(self):
        """Versioning fields included in to_dict."""
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="version-test-002",
            content="Test advisory",
            evidence_refs=[],
            suggestion_payload={},
        )
        
        data = advisory.to_dict()
        assert "generator_id" in data
        assert "model_version" in data
        assert "scoring_method" in data
        assert "calibration_version" in data
    
    def test_advisory_versioning_in_canonical(self):
        """Versioning fields included in canonical JSON."""
        advisory = create_routing_suggestion(
            source_model="mem-snn/v1",
            job_seed="version-test-003",
            content="Test advisory",
            evidence_refs=[],
            suggestion_payload={},
        )
        
        canonical = advisory.to_canonical_json()
        assert "generator_id" in canonical
        assert "model_version" in canonical
    
    def test_persist_advisory_with_versioning(self, db_path):
        """Advisory persists with full versioning."""
        version = AdvisoryVersion(
            generator_id="mem-snn-shadow-v2",
            model_version="2026-01-24-b",
            scoring_method="real",
            calibration_version="v1.1"
        )
        
        persist_advisory_output(
            advisory_id="adv-version-001",
            job_seed="persist-version-001",
            source_model="mem-snn/v2",
            version=version,
            scope="router",
            advice_type="routing_suggestion",
            content="Versioned advisory",
            confidence_estimate="medium",
            canonical_json='{"test": true}',
            signature="sig123",
            db_path=db_path
        )
        
        stored = get_advisory_by_id("adv-version-001", db_path)
        assert stored["generator_id"] == "mem-snn-shadow-v2"
        assert stored["model_version"] == "2026-01-24-b"
        assert stored["scoring_method"] == "real"


class TestReplayFidelity:
    """P0 Item 4: Explicit replay model."""
    
    @pytest.fixture
    def db_path(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_database(path)
        yield path
        os.unlink(path)
    
    def test_replay_verification_pass(self, db_path):
        """Replay with identical canonical JSON should pass."""
        canonical = '{"test":"data","version":"1.0"}'
        
        persist_advisory_output(
            advisory_id="replay-001",
            job_seed="replay-test-001",
            source_model="test",
            version=AdvisoryVersion("gen1", "v1", "shadow", "c1"),
            scope="router",
            advice_type="routing_suggestion",
            content="Test",
            confidence_estimate="medium",
            canonical_json=canonical,
            signature="sig",
            db_path=db_path
        )
        
        # Verify replay matches
        assert verify_advisory_replay("replay-001", canonical, db_path) == True
    
    def test_replay_verification_fail(self, db_path):
        """Replay with different canonical JSON should fail."""
        persist_advisory_output(
            advisory_id="replay-002",
            job_seed="replay-test-002",
            source_model="test",
            version=AdvisoryVersion("gen1", "v1", "shadow", "c1"),
            scope="router",
            advice_type="routing_suggestion",
            content="Test",
            confidence_estimate="medium",
            canonical_json='{"original":"data"}',
            signature="sig",
            db_path=db_path
        )
        
        # Different canonical should fail
        assert verify_advisory_replay("replay-002", '{"different":"data"}', db_path) == False
    
    def test_replay_divergence_logged(self, db_path):
        """Replay divergence is logged as quarantine event."""
        log_replay_divergence(
            job_seed="diverge-001",
            original_signature="sig-orig",
            replay_signature="sig-replay",
            divergence_details="Signature mismatch",
            db_path=db_path
        )
        
        entries = get_reflective_log_entries(
            job_seed="diverge-001",
            event_type="REPLAY_DIVERGENCE",
            db_path=db_path
        )
        
        assert len(entries) == 1
        import json
        payload = json.loads(entries[0]["payload"])
        assert payload["quarantine"] == True
    
    def test_full_replay_verification(self, db_path):
        """Full replay verification with entry list."""
        original = [
            {"event_id": "1", "immutable_signature": "sig-a"},
            {"event_id": "2", "immutable_signature": "sig-b"},
        ]
        
        replay_same = [
            {"event_id": "1", "immutable_signature": "sig-a"},
            {"event_id": "2", "immutable_signature": "sig-b"},
        ]
        
        replay_diff = [
            {"event_id": "1", "immutable_signature": "sig-a"},
            {"event_id": "2", "immutable_signature": "sig-DIFFERENT"},
        ]
        
        assert verify_replay_fidelity("same-001", original, replay_same, db_path) == True
        assert verify_replay_fidelity("diff-001", original, replay_diff, db_path) == False


class TestDivergenceStats:
    """Test divergence tracking statistics."""
    
    @pytest.fixture
    def db_path(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_database(path)
        yield path
        os.unlink(path)
    
    def test_divergence_stats_work(self, db_path):
        """Divergence statistics are computed."""
        persist_meta_observation(
            observation_id="obs-001",
            job_seed="stats-001",
            advisory_id="adv-001",
            divergence_type="route_ignored",
            divergence_description="Test",
            impact_estimate="minor",
            actual_outcome="agent_general",
            canonical_json="{}",
            signature="sig",
            db_path=db_path
        )
        
        persist_meta_observation(
            observation_id="obs-002",
            job_seed="stats-002",
            advisory_id="adv-002",
            divergence_type="route_ignored",
            divergence_description="Test2",
            impact_estimate="minor",
            actual_outcome="agent_general",
            canonical_json="{}",
            signature="sig",
            db_path=db_path
        )
        
        persist_meta_observation(
            observation_id="obs-003",
            job_seed="stats-003",
            advisory_id="adv-003",
            divergence_type="no_divergence",
            divergence_description="Match",
            impact_estimate="negligible",
            actual_outcome="agent_math",
            canonical_json="{}",
            signature="sig",
            db_path=db_path
        )
        
        stats = get_divergence_stats(db_path)
        assert stats["route_ignored"] == 2
        assert stats["no_divergence"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
