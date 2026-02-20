#!/usr/bin/env python3
"""
Parameter Sweep Runner

Generates diverse training data by replaying episodic history under different world variants.
Deterministic: Same facts → Different candidates → Different approvals → Different outcomes

Sweep parameters:
- novelty_weight
- promotion_threshold
- consistency_threshold
"""
import os
import sys
import json
import sqlite3
import copy
from typing import Dict, List

# Setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from mace.core import deterministic, canonical
from mace.memory import consolidator, rewards
from mace.governance import admin


# =============================================================================
# World Variants (Deterministic Parameter Sweeps)
# =============================================================================

WORLD_VARIANTS = {
    "world_A_low_novelty": {
        "novelty_weight": 0.2,
        "promotion_threshold": 0.6,
        "consistency_threshold": 0.6,
        "description": "Low novelty weight, permissive thresholds"
    },
    "world_B_balanced": {
        "novelty_weight": 0.4,
        "promotion_threshold": 0.75,
        "consistency_threshold": 0.8,
        "description": "Balanced weights, moderate thresholds"
    },
    "world_C_high_novelty": {
        "novelty_weight": 0.6,
        "promotion_threshold": 0.9,
        "consistency_threshold": 0.95,
        "description": "High novelty weight, strict thresholds"
    },
}


def compute_consolidator_score_with_weights(features: Dict, weights: Dict) -> float:
    """
    Re-compute consolidator score with custom weights.
    """
    if features.get("governance_conflict_flag", False):
        return 0.1
    
    # Custom weights
    novelty_weight = weights.get("novelty_weight", 0.4)
    
    # Distribute remaining weight across other features
    remaining = 1.0 - novelty_weight
    freq_w = remaining * 0.25
    rec_w = remaining * 0.15
    cons_w = remaining * 0.35
    div_w = remaining * 0.25
    
    score = (
        features["frequency"] * freq_w +
        features["recency"] * rec_w +
        features["consistency"] * cons_w +
        features["semantic_novelty"] * novelty_weight +
        features["source_diversity"] * div_w
    )
    return round(score, 3)


def apply_governance_with_threshold(
    candidate: Dict,
    threshold: float,
    consistency_threshold: float
) -> tuple:
    """
    Apply governance decision based on thresholds.
    Returns (decision, reason)
    """
    features = candidate["features"]
    score = candidate["consolidator_score"]
    
    # Check governance conflict flag first
    if features.get("governance_conflict_flag", False):
        return ("rejected", "governance_conflict")
    
    # Check consistency threshold
    if features["consistency"] < consistency_threshold:
        return ("rejected", "low_consistency")
    
    # Check promotion threshold
    if score >= threshold:
        return ("approved", "meets_threshold")
    else:
        return ("rejected", "below_threshold")


def run_parameter_sweep(
    episodes: List[Dict],
    variant_name: str,
    variant_config: Dict,
    current_tick: int,
    sem_state: Dict[str, str],
    db_path: str = None
) -> Dict:
    """
    Run a single parameter sweep variant.
    
    Returns:
        Sweep results with candidates, labels, and statistics
    """
    # Initialize deterministic seed for this variant
    deterministic.init_seed(f"sweep_{variant_name}")
    
    # Cluster episodes (same clustering, different scoring)
    clusters = consolidator.cluster_episodes(episodes, user_id=f"sweep_{variant_name}")
    
    # Generate candidates with modified scoring
    candidates = []
    for cluster in clusters:
        # Compute features
        features = consolidator.compute_features(cluster, episodes, list(sem_state.keys()))
        
        # Apply custom weights
        custom_score = compute_consolidator_score_with_weights(
            features, 
            {"novelty_weight": variant_config["novelty_weight"]}
        )
        
        # Generate candidate
        provenance = cluster.get_member_ids()
        candidate_payload = f"{cluster.canonical_key}:{cluster.normalized_value}:{','.join(sorted(provenance))}:{variant_name}"
        candidate_id = deterministic.deterministic_id("sweep_candidate", candidate_payload)
        
        candidate = {
            "candidate_id": candidate_id,
            "features": features,
            "proposed_key": cluster.canonical_key,
            "value": cluster.normalized_value or "",
            "provenance": provenance,
            "consolidator_score": custom_score,
            "mem_snn_score": consolidator.compute_mem_snn_shadow_score(features),
            "variant": variant_name,
        }
        candidates.append(candidate)
    
    # Apply governance with variant thresholds
    labels = []
    approved_count = 0
    rejected_count = 0
    
    for candidate in candidates:
        decision, reason = apply_governance_with_threshold(
            candidate,
            variant_config["promotion_threshold"],
            variant_config["consistency_threshold"]
        )
        
        # Compute full multi-dimensional label
        label = rewards.compute_full_label(
            candidate, current_tick, sem_state,
            "approved" if decision == "approved" else "rejected"
        )
        label["reason"] = reason
        label["variant"] = variant_name
        
        labels.append(label)
        
        if decision == "approved":
            approved_count += 1
        else:
            rejected_count += 1
    
    return {
        "variant_name": variant_name,
        "config": variant_config,
        "candidates": candidates,
        "labels": labels,
        "stats": {
            "total": len(candidates),
            "approved": approved_count,
            "rejected": rejected_count,
        }
    }


def run_all_sweeps(
    episodes: List[Dict],
    current_tick: int = 12,
    sem_state: Dict[str, str] = None,
    output_dir: str = "training_artifacts/sweeps"
) -> List[Dict]:
    """
    Run all parameter sweep variants.
    """
    if sem_state is None:
        sem_state = {}
    
    os.makedirs(output_dir, exist_ok=True)
    
    all_results = []
    
    for variant_name, variant_config in WORLD_VARIANTS.items():
        print(f"\n=== Running sweep: {variant_name} ===")
        print(f"  Config: {variant_config}")
        
        result = run_parameter_sweep(
            episodes, variant_name, variant_config,
            current_tick, sem_state
        )
        
        print(f"  Results: {result['stats']}")
        all_results.append(result)
        
        # Save variant results
        with open(f"{output_dir}/{variant_name}_candidates.jsonl", "w") as f:
            for c in result["candidates"]:
                f.write(json.dumps(c) + "\n")
        
        with open(f"{output_dir}/{variant_name}_labels.jsonl", "w") as f:
            for l in result["labels"]:
                f.write(json.dumps(l) + "\n")
    
    # Save combined summary
    summary = {
        "sweep_type": "parameter",
        "variants": [r["variant_name"] for r in all_results],
        "stats": {r["variant_name"]: r["stats"] for r in all_results},
    }
    with open(f"{output_dir}/sweep_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n=== Sweep Complete ===")
    print(f"  Variants: {len(all_results)}")
    for r in all_results:
        print(f"    {r['variant_name']}: {r['stats']}")
    
    return all_results


if __name__ == "__main__":
    print("Parameter Sweep Runner")
    print("Usage: python sweep_worlds.py")
    print("(Requires episodes to be loaded first)")
