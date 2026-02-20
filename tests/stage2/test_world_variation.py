"""
Stage-2 Phase 2.6 Tests: Structured Diversity (World Variation)

Purpose: Verify diversity comes from world variation, not randomness.

Pass Criteria:
- Same seed + same world = same outcome
- Different world configs = different labels
- Forbidden sources rejected
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from mace.core import deterministic
from mace.stage2 import world_variation


class TestApprovedDiversitySources(unittest.TestCase):
    """Test approved and forbidden diversity sources."""
    
    def test_approved_sources_defined(self):
        """Verify approved sources are defined."""
        expected = [
            "governance_policy_sweep",
            "parameter_threshold_sweep",
            "time_shifted_sem_snapshot",
            "agent_disagreement",
            "governance_variance"
        ]
        self.assertEqual(world_variation.APPROVED_DIVERSITY_SOURCES, expected)
    
    def test_forbidden_sources_defined(self):
        """Verify forbidden sources are defined."""
        self.assertIn("noise_injection", world_variation.FORBIDDEN_DIVERSITY_SOURCES)
        self.assertIn("random_labels", world_variation.FORBIDDEN_DIVERSITY_SOURCES)
    
    def test_approved_source_check(self):
        """Verify approved source check works."""
        self.assertTrue(world_variation.is_approved_diversity_source("governance_policy_sweep"))
        self.assertFalse(world_variation.is_approved_diversity_source("noise_injection"))
    
    def test_forbidden_source_check(self):
        """Verify forbidden source check works."""
        self.assertTrue(world_variation.is_forbidden_diversity_source("noise_injection"))
        self.assertTrue(world_variation.is_forbidden_diversity_source("random_labels"))
        self.assertFalse(world_variation.is_forbidden_diversity_source("governance_policy_sweep"))


class TestWorldConfig(unittest.TestCase):
    """Test world configuration."""
    
    def test_create_world_config(self):
        """Verify world config creation."""
        world = world_variation.create_world_config(
            world_id="test_world",
            governance_policy="strict",
            threshold_config={"frequency_min": 5}
        )
        
        self.assertEqual(world.world_id, "test_world")
        self.assertEqual(world.governance_policy, "strict")
        self.assertEqual(world.threshold_config["frequency_min"], 5)
    
    def test_world_config_to_dict(self):
        """Verify world config serialization."""
        world = world_variation.create_world_config(
            world_id="json_test",
            governance_policy="default"
        )
        
        d = world.to_dict()
        self.assertIn("world_id", d)
        self.assertIn("governance_policy", d)


class TestDeterminism(unittest.TestCase):
    """Test determinism verification."""
    
    def test_same_seed_same_world_same_hash(self):
        """Verify same seed + same world produces same hash."""
        world = world_variation.create_world_config(
            world_id="det_test",
            governance_policy="default"
        )
        
        hash1 = world_variation.verify_determinism("test_seed", world)
        hash2 = world_variation.verify_determinism("test_seed", world)
        
        self.assertEqual(hash1, hash2)
    
    def test_different_world_different_hash(self):
        """Verify different world produces different hash."""
        world1 = world_variation.create_world_config(
            world_id="world_1",
            governance_policy="strict"
        )
        world2 = world_variation.create_world_config(
            world_id="world_2",
            governance_policy="permissive"
        )
        
        hash1 = world_variation.verify_determinism("test_seed", world1)
        hash2 = world_variation.verify_determinism("test_seed", world2)
        
        self.assertNotEqual(hash1, hash2)


class TestWorldSweeps(unittest.TestCase):
    """Test world sweep generation."""
    
    def test_governance_policy_sweep(self):
        """Verify governance policy sweep generates worlds."""
        worlds = world_variation.generate_governance_policy_sweep()
        
        self.assertGreater(len(worlds), 0)
        
        policies = [w.governance_policy for w in worlds]
        self.assertIn("strict", policies)
        self.assertIn("permissive", policies)
    
    def test_agent_disagreement_sweep(self):
        """Verify agent disagreement sweep generates worlds."""
        worlds = world_variation.generate_agent_disagreement_sweep()
        
        self.assertGreater(len(worlds), 0)
        
        # Check different agent configs
        configs = [w.agent_config for w in worlds]
        self.assertTrue(any("weight_truth" in c for c in configs))
    
    def test_time_shift_sweep(self):
        """Verify time shift sweep generates worlds."""
        worlds = world_variation.generate_time_shift_sweep()
        
        self.assertGreater(len(worlds), 0)
        
        offsets = [w.time_offset_ticks for w in worlds]
        self.assertIn(0, offsets)
        self.assertTrue(any(o < 0 for o in offsets))
        self.assertTrue(any(o > 0 for o in offsets))
    
    def test_all_world_variations(self):
        """Verify combined world sweep works."""
        all_worlds = world_variation.generate_all_world_variations()
        
        # Should have multiple worlds
        self.assertGreater(len(all_worlds), 10)
        
        # Should have unique world IDs
        world_ids = [w.world_id for w in all_worlds]
        self.assertEqual(len(world_ids), len(set(world_ids)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
