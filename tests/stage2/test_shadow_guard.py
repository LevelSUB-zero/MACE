"""
Stage-2 Phase 2.0 Tests: Shadow Guard Enforcement

Purpose: Verify that shadow mode is enforced and violations are caught.
Spec: docs/stage2_ideology.md, docs/stage2_failure_modes.md

Pass Criteria:
- MEM_LEARNING_MODE is always "shadow"
- LearningShadowViolation is raised on any breach
- Removing MEM-SNN produces identical system behavior
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from mace.stage2 import shadow_guard
from mace.config import config_loader


class TestShadowGuardEnforcement(unittest.TestCase):
    """Test shadow mode enforcement."""
    
    def setUp(self):
        """Clean up any kill-switch state before each test."""
        if os.path.exists(shadow_guard.STAGE2_KILLSWITCH_FILE):
            os.remove(shadow_guard.STAGE2_KILLSWITCH_FILE)
    
    def tearDown(self):
        """Clean up kill-switch state after each test."""
        if os.path.exists(shadow_guard.STAGE2_KILLSWITCH_FILE):
            os.remove(shadow_guard.STAGE2_KILLSWITCH_FILE)
    
    def test_learning_mode_is_shadow(self):
        """Verify MEM_LEARNING_MODE is always shadow."""
        mode = config_loader.get_learning_mode()
        self.assertEqual(mode, "shadow", 
                        "MEM_LEARNING_MODE must be 'shadow' in Stage-2")
    
    def test_shadow_guard_get_learning_mode(self):
        """Verify shadow_guard.get_learning_mode() returns shadow."""
        mode = shadow_guard.get_learning_mode()
        self.assertEqual(mode, "shadow")
    
    def test_assert_shadow_mode_passes(self):
        """Verify assert_shadow_mode() does not raise when in shadow mode."""
        # Should not raise
        shadow_guard.assert_shadow_mode("test_module")
    
    def test_guard_against_consumption_always_fails(self):
        """Verify guard_against_consumption always raises in Stage-2."""
        with self.assertRaises(shadow_guard.LearningShadowViolation):
            shadow_guard.guard_against_consumption("test_output", "test_module")
        
        # Verify kill-switch was activated
        self.assertTrue(shadow_guard.is_stage2_halted())
    
    def test_guard_router_access_blocks_mem_snn(self):
        """Verify Router guard blocks MEM-SNN access."""
        with self.assertRaises(shadow_guard.LearningShadowViolation):
            shadow_guard.guard_router_access("mem_snn_score")
    
    def test_guard_router_access_allows_non_learning(self):
        """Verify Router guard allows non-learning score sources."""
        # Should not raise for normal sources
        shadow_guard.guard_router_access("heuristic_score")
        shadow_guard.guard_router_access("rule_based_decision")
    
    def test_guard_executor_access_blocks_candidate_score(self):
        """Verify Executor guard blocks candidate score access."""
        with self.assertRaises(shadow_guard.LearningShadowViolation):
            shadow_guard.guard_executor_access("candidate_score_threshold")
    
    def test_guard_sem_write_blocks_auto_trigger(self):
        """Verify SEM writer guard blocks auto-triggered writes."""
        with self.assertRaises(shadow_guard.LearningShadowViolation):
            shadow_guard.guard_sem_write("council_label_auto_trigger")
    
    def test_guard_sem_write_allows_governance_approved(self):
        """Verify SEM writer guard allows governance-approved writes."""
        # Should not raise for governance-approved
        shadow_guard.guard_sem_write("council_label_governance_approved")
    
    def test_killswitch_toggles(self):
        """Verify kill-switch state management."""
        # Initially not halted
        self.assertFalse(shadow_guard.is_stage2_halted())
        
        # After violation, halted
        try:
            shadow_guard.guard_against_consumption("test", "test")
        except shadow_guard.LearningShadowViolation:
            pass
        
        self.assertTrue(shadow_guard.is_stage2_halted())
    
    def test_assert_shadow_mode_fails_when_halted(self):
        """Verify assert_shadow_mode fails when Stage-2 is halted."""
        # Activate kill-switch manually
        shadow_guard._activate_stage2_killswitch("test_halt", "test_module")
        
        with self.assertRaises(shadow_guard.LearningShadowViolation):
            shadow_guard.assert_shadow_mode("test_caller")


class TestCandidateFeatures(unittest.TestCase):
    """Test candidate feature set is locked."""
    
    def test_feature_set_locked(self):
        """Verify exactly 6 features in the locked set."""
        features = config_loader.get_candidate_features()
        
        expected = [
            'frequency',
            'consistency',
            'recency',
            'source_diversity',
            'semantic_novelty',
            'governance_conflict_flag'
        ]
        
        self.assertEqual(features, expected,
                        "Candidate feature set must be exactly the 6 locked features")
    
    def test_feature_count(self):
        """Verify feature count is exactly 6."""
        features = config_loader.get_candidate_features()
        self.assertEqual(len(features), 6, "Must have exactly 6 features")


class TestStage2ConfigIntegrity(unittest.TestCase):
    """Test Stage-2 config file integrity."""
    
    def test_config_loads(self):
        """Verify Stage-2 config loads without error."""
        config = config_loader.get_stage2_config()
        self.assertIsNotNone(config)
    
    def test_config_has_required_keys(self):
        """Verify all required config keys exist."""
        config = config_loader.get_stage2_config()
        
        required_keys = [
            'MEM_LEARNING_MODE',
            'SHADOW_TABLE',
            'DIVERGENCE_TABLE',
            'EVENT_LOG_TABLE',
            'CANDIDATE_FEATURES'
        ]
        
        for key in required_keys:
            self.assertIn(key, config, f"Config must contain '{key}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
