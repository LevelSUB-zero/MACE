#!/usr/bin/env python3
"""
Governance Policy Sweep Runner

Freeze episodic data and sweep governance policies deterministically.
Learning emerges when policies disagree.

Policies:
- P1: strict_consistency (consistency > 0.8)
- P2: frequency_boost (consistency > 0.6 AND frequency > 0.4)
- P3: novelty_focus (novelty > 0.5 AND diversity > 0.3)
- P4: conflict_aware (NOT governance_conflict_flag)
"""
import os
import sys
import json
from typing import Dict, List, Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from mace.core import deterministic
from mace.memory import consolidator, rewards


# =============================================================================
# Governance Policies
# =============================================================================

def policy_strict_consistency(features: Dict, score: float) -> tuple:
    """P1: Strict consistency requirement"""
    if features["consistency"] > 0.8 and not features.get("governance_conflict_flag", False):
        return ("approved", "high_consistency")
    return ("rejected", "low_consistency")


def policy_frequency_boost(features: Dict, score: float) -> tuple:
    """P2: Frequency + moderate consistency"""
    if (features["consistency"] > 0.6 and 
        features["frequency"] > 0.4 and 
        not features.get("governance_conflict_flag", False)):
        return ("approved", "frequency_consistency_combo")
    return ("rejected", "insufficient_frequency_consistency")


def policy_novelty_focus(features: Dict, score: float) -> tuple:
    """P3: Novelty + source diversity"""
    if (features["semantic_novelty"] > 0.5 and 
        features["source_diversity"] > 0.3 and 
        not features.get("governance_conflict_flag", False)):
        return ("approved", "novel_diverse")
    return ("rejected", "not_novel_or_diverse")


def policy_conflict_aware(features: Dict, score: float) -> tuple:
    """P4: Only reject if conflict flag is set"""
    if not features.get("governance_conflict_flag", False):
        return ("approved", "no_conflict")
    return ("rejected", "conflict_detected")


def policy_score_threshold(features: Dict, score: float) -> tuple:
    """P5: Simple score threshold (baseline)"""
    if score >= 0.5 and not features.get("governance_conflict_flag", False):
        return ("approved", "meets_score_threshold")
    return ("rejected", "below_threshold_or_conflict")


GOVERNANCE_POLICIES = {
    "P1_strict_consistency": policy_strict_consistency,
    "P2_frequency_boost": policy_frequency_boost,
    "P3_novelty_focus": policy_novelty_focus,
    "P4_conflict_aware": policy_conflict_aware,
    "P5_score_threshold": policy_score_threshold,
}


def run_policy_sweep(
    candidates: List[Dict],
    policy_name: str,
    policy_fn: Callable,
    current_tick: int,
    sem_state: Dict[str, str]
) -> Dict:
    """
    Run a single policy sweep.
    """
    labels = []
    approved_count = 0
    rejected_count = 0
    
    for candidate in candidates:
        features = candidate["features"]
        score = candidate["consolidator_score"]
        
        decision, reason = policy_fn(features, score)
        
        # Compute full label
        label = rewards.compute_full_label(
            candidate, current_tick, sem_state,
            "approved" if decision == "approved" else "rejected"
        )
        label["reason"] = reason
        label["policy"] = policy_name
        
        labels.append(label)
        
        if decision == "approved":
            approved_count += 1
        else:
            rejected_count += 1
    
    return {
        "policy_name": policy_name,
        "labels": labels,
        "stats": {
            "total": len(candidates),
            "approved": approved_count,
            "rejected": rejected_count,
            "approval_rate": approved_count / len(candidates) if candidates else 0,
        }
    }


def run_all_policy_sweeps(
    candidates: List[Dict],
    current_tick: int = 12,
    sem_state: Dict[str, str] = None,
    output_dir: str = "training_artifacts/policy_sweeps"
) -> List[Dict]:
    """
    Run all governance policy sweeps.
    """
    if sem_state is None:
        sem_state = {}
    
    os.makedirs(output_dir, exist_ok=True)
    
    all_results = []
    
    for policy_name, policy_fn in GOVERNANCE_POLICIES.items():
        print(f"\n=== Running policy: {policy_name} ===")
        
        result = run_policy_sweep(
            candidates, policy_name, policy_fn,
            current_tick, sem_state
        )
        
        print(f"  Stats: {result['stats']}")
        all_results.append(result)
        
        # Save policy results
        with open(f"{output_dir}/{policy_name}_labels.jsonl", "w") as f:
            for l in result["labels"]:
                f.write(json.dumps(l) + "\n")
    
    # Analyze policy disagreements
    disagreements = analyze_policy_disagreements(all_results, candidates)
    
    # Save summary
    summary = {
        "sweep_type": "policy",
        "policies": [r["policy_name"] for r in all_results],
        "stats": {r["policy_name"]: r["stats"] for r in all_results},
        "disagreements": disagreements,
    }
    with open(f"{output_dir}/policy_sweep_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n=== Policy Sweep Complete ===")
    print(f"  Policies: {len(all_results)}")
    print(f"  Disagreement examples: {len(disagreements)}")
    
    return all_results


def analyze_policy_disagreements(
    results: List[Dict],
    candidates: List[Dict]
) -> List[Dict]:
    """
    Find candidates where policies disagree.
    These are the most valuable training examples.
    """
    disagreements = []
    
    # Build decision map: candidate_id -> {policy: decision}
    decision_map = {}
    for candidate in candidates:
        cid = candidate["candidate_id"]
        decision_map[cid] = {"candidate": candidate, "decisions": {}}
    
    for result in results:
        policy_name = result["policy_name"]
        for label in result["labels"]:
            cid = label["candidate_id"]
            if cid in decision_map:
                decision_map[cid]["decisions"][policy_name] = label["governance_decision"]
    
    # Find disagreements
    for cid, data in decision_map.items():
        decisions = set(data["decisions"].values())
        if len(decisions) > 1:  # Not all policies agree
            disagreements.append({
                "candidate_id": cid,
                "proposed_key": data["candidate"]["proposed_key"],
                "value": data["candidate"]["value"],
                "decisions": data["decisions"],
                "conflict_type": "mixed" if "approved" in decisions and "rejected" in decisions else "unanimous",
            })
    
    return disagreements


if __name__ == "__main__":
    print("Governance Policy Sweep Runner")
    print("Usage: python sweep_policies.py")
    print("(Requires candidates to be loaded first)")
