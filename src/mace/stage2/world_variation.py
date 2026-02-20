"""
Stage-2 Structured Diversity (World Variation) (AUTHORITATIVE)

Purpose: World diversity, not randomness.
Spec: Section G of Stage-2 governance spec

Core Doctrine:
- Determinism ≠ sameness
- Determinism = reproducibility
- Same seed + same world → same outcome
- Same seed + different world → different truth

APPROVED DIVERSITY SOURCES:
- Policy disagreement
- Temporal shifts
- World parameterization
- Agent disagreement
- Governance variance

FORBIDDEN SOURCES:
- Noise injection
- Random labels
- Stochastic perturbations
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from mace.core import deterministic


# =============================================================================
# DIVERSITY SOURCE TYPES (APPROVED)
# =============================================================================

APPROVED_DIVERSITY_SOURCES = [
    "governance_policy_sweep",
    "parameter_threshold_sweep", 
    "time_shifted_sem_snapshot",
    "agent_disagreement",
    "governance_variance"
]

FORBIDDEN_DIVERSITY_SOURCES = [
    "noise_injection",
    "random_labels",
    "stochastic_perturbation",
    "random_sampling"
]


def is_approved_diversity_source(source_type: str) -> bool:
    """Check if a diversity source is approved."""
    return source_type in APPROVED_DIVERSITY_SOURCES


def is_forbidden_diversity_source(source_type: str) -> bool:
    """Check if a diversity source is forbidden."""
    for forbidden in FORBIDDEN_DIVERSITY_SOURCES:
        if forbidden in source_type.lower():
            return True
    return False


# =============================================================================
# WORLD CONFIGURATION (PARAMETERIZED DIVERSITY)
# =============================================================================

@dataclass
class WorldConfig:
    """
    A world configuration for structured diversity.
    
    Different world configs produce different "truths" from the same seed.
    This is the correct way to generate training diversity.
    """
    world_id: str
    governance_policy: str  # e.g., "strict", "permissive", "default"
    threshold_config: Dict[str, float]  # e.g., {"frequency_min": 3, "consistency_min": 0.8}
    time_offset_ticks: int  # Temporal shift from baseline
    agent_config: Dict[str, Any]  # Agent-specific parameters
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "world_id": self.world_id,
            "governance_policy": self.governance_policy,
            "threshold_config": self.threshold_config,
            "time_offset_ticks": self.time_offset_ticks,
            "agent_config": self.agent_config
        }


def create_world_config(
    world_id: str,
    governance_policy: str = "default",
    threshold_config: Dict[str, float] = None,
    time_offset_ticks: int = 0,
    agent_config: Dict[str, Any] = None
) -> WorldConfig:
    """Create a world configuration."""
    return WorldConfig(
        world_id=world_id,
        governance_policy=governance_policy,
        threshold_config=threshold_config or {},
        time_offset_ticks=time_offset_ticks,
        agent_config=agent_config or {}
    )


# =============================================================================
# GOVERNANCE POLICY SWEEPS
# =============================================================================

def generate_governance_policy_sweep() -> List[WorldConfig]:
    """
    Generate world configs for governance policy sweep.
    
    This varies the governance policy to create diverse labels
    for the same underlying data.
    """
    policies = [
        ("strict", {"frequency_min": 5, "consistency_min": 0.9}),
        ("default", {"frequency_min": 3, "consistency_min": 0.7}),
        ("permissive", {"frequency_min": 1, "consistency_min": 0.5}),
        ("safety_first", {"frequency_min": 3, "consistency_min": 0.7, "safety_override": True}),
        ("utility_first", {"frequency_min": 2, "consistency_min": 0.6, "utility_boost": True})
    ]
    
    worlds = []
    for policy_name, thresholds in policies:
        world = create_world_config(
            world_id=f"policy_{policy_name}",
            governance_policy=policy_name,
            threshold_config=thresholds
        )
        worlds.append(world)
    
    return worlds


# =============================================================================
# PARAMETER THRESHOLD SWEEPS
# =============================================================================

def generate_threshold_sweep(
    param_name: str,
    values: List[float]
) -> List[WorldConfig]:
    """
    Generate world configs by sweeping a specific parameter.
    
    Args:
        param_name: Name of the threshold parameter to sweep
        values: List of values to use
    
    Returns:
        List of world configs, one per value
    """
    worlds = []
    for i, value in enumerate(values):
        world = create_world_config(
            world_id=f"sweep_{param_name}_{i}",
            governance_policy="sweep",
            threshold_config={param_name: value}
        )
        worlds.append(world)
    
    return worlds


# =============================================================================
# TIME-SHIFTED SEM SNAPSHOTS
# =============================================================================

def generate_time_shift_sweep(
    offsets: List[int] = None
) -> List[WorldConfig]:
    """
    Generate world configs for time-shifted SEM snapshots.
    
    This creates diversity by looking at memory at different
    points in time.
    
    Args:
        offsets: List of tick offsets (default: [-10, -5, 0, 5, 10])
    
    Returns:
        List of world configs with different time offsets
    """
    if offsets is None:
        offsets = [-10, -5, 0, 5, 10]
    
    worlds = []
    for offset in offsets:
        world = create_world_config(
            world_id=f"time_offset_{offset:+d}",
            governance_policy="default",
            time_offset_ticks=offset
        )
        worlds.append(world)
    
    return worlds


# =============================================================================
# AGENT DISAGREEMENT SIMULATION
# =============================================================================

def generate_agent_disagreement_sweep() -> List[WorldConfig]:
    """
    Generate world configs simulating agent disagreement.
    
    Different agent configurations lead to different council outcomes,
    providing natural diversity without randomness.
    """
    agent_configs = [
        ("truth_focused", {"weight_truth": 2.0, "weight_utility": 1.0, "weight_safety": 1.0}),
        ("safety_focused", {"weight_truth": 1.0, "weight_utility": 1.0, "weight_safety": 2.0}),
        ("utility_focused", {"weight_truth": 1.0, "weight_utility": 2.0, "weight_safety": 1.0}),
        ("balanced", {"weight_truth": 1.0, "weight_utility": 1.0, "weight_safety": 1.0})
    ]
    
    worlds = []
    for agent_name, config in agent_configs:
        world = create_world_config(
            world_id=f"agent_{agent_name}",
            governance_policy="default",
            agent_config=config
        )
        worlds.append(world)
    
    return worlds


# =============================================================================
# COMBINED WORLD SWEEP
# =============================================================================

def generate_all_world_variations() -> List[WorldConfig]:
    """
    Generate all approved world variations for training diversity.
    
    This is the master function that combines all diversity sources.
    """
    all_worlds = []
    
    # Add governance policy sweep
    all_worlds.extend(generate_governance_policy_sweep())
    
    # Add agent disagreement sweep
    all_worlds.extend(generate_agent_disagreement_sweep())
    
    # Add time shift sweep
    all_worlds.extend(generate_time_shift_sweep())
    
    return all_worlds


# =============================================================================
# DETERMINISM VERIFICATION
# =============================================================================

def verify_determinism(seed: str, world: WorldConfig) -> str:
    """
    Generate a deterministic hash for a seed + world combination.
    
    Same seed + same world → same hash (reproducible)
    """
    deterministic.init_seed(seed)
    
    world_json = json.dumps(world.to_dict(), sort_keys=True)
    combined = f"{seed}:{world_json}"
    
    return deterministic.deterministic_id("world_verify", combined)
