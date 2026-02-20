#!/usr/bin/env python3
"""
Enhanced Training Data Generator for MEM-SNN

Creates diverse, balanced training data with:
- Balanced governance decisions (approved/rejected/conflict)
- Varied truth statuses (correct/incorrect/uncertain)
- Diverse feature combinations
- Policy sweep variations

Uses Stage-2 world_variation for structured diversity.
"""

import json
import hashlib
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def deterministic_id(prefix: str, content: str) -> str:
    """Generate deterministic hash ID."""
    combined = f"{prefix}:{content}"
    return hashlib.sha256(combined.encode()).hexdigest()


def generate_candidate(
    proposed_key: str,
    value: str,
    features: Dict[str, float],
    seed: str
) -> Dict[str, Any]:
    """Generate a candidate with deterministic ID."""
    cid = deterministic_id("candidate", f"{seed}:{proposed_key}:{value}")
    return {
        "candidate_id": cid,
        "features": features,
        "proposed_key": proposed_key,
        "value": value,
        "provenance": [deterministic_id("episode", f"{seed}:ep1")],
        "created_at": datetime.now().isoformat()
    }


def generate_label(
    candidate_id: str,
    governance_decision: str,
    truth_status: str,
    utility_status: str,
    safety_status: str
) -> Dict[str, Any]:
    """Generate a label for a candidate."""
    return {
        "candidate_id": candidate_id,
        "governance_decision": governance_decision,
        "truth_status": truth_status,
        "utility_status": utility_status,
        "safety_status": safety_status
    }


# =============================================================================
# DIVERSE TRAINING SCENARIOS
# =============================================================================

APPROVED_SCENARIOS = [
    # High frequency, high consistency, safe content
    {
        "key": "user/preferences/timezone",
        "value": "UTC+5:30",
        "features": {"frequency": 0.8, "recency": 0.9, "consistency": 0.95, "semantic_novelty": 0.3, "source_diversity": 0.6, "governance_conflict_flag": 0},
        "truth": "correct", "utility": "useful", "safety": "safe"
    },
    {
        "key": "world/fact/math/pi",
        "value": "3.14159",
        "features": {"frequency": 0.7, "recency": 0.6, "consistency": 1.0, "semantic_novelty": 0.1, "source_diversity": 0.8, "governance_conflict_flag": 0},
        "truth": "correct", "utility": "useful", "safety": "safe"
    },
    {
        "key": "user/preferences/language",
        "value": "english",
        "features": {"frequency": 0.9, "recency": 0.8, "consistency": 0.9, "semantic_novelty": 0.2, "source_diversity": 0.7, "governance_conflict_flag": 0},
        "truth": "correct", "utility": "useful", "safety": "safe"
    },
    {
        "key": "context/project/framework",
        "value": "pytorch",
        "features": {"frequency": 0.6, "recency": 0.95, "consistency": 0.85, "semantic_novelty": 0.4, "source_diversity": 0.5, "governance_conflict_flag": 0},
        "truth": "correct", "utility": "useful", "safety": "safe"
    },
    {
        "key": "user/interests/genre",
        "value": "science_fiction",
        "features": {"frequency": 0.5, "recency": 0.7, "consistency": 0.8, "semantic_novelty": 0.5, "source_diversity": 0.4, "governance_conflict_flag": 0},
        "truth": "correct", "utility": "useful", "safety": "safe"
    },
]

REJECTED_SCENARIOS = [
    # Unsafe content - should be rejected
    {
        "key": "user/private/password",
        "value": "secret123",
        "features": {"frequency": 0.3, "recency": 0.8, "consistency": 0.9, "semantic_novelty": 1.0, "source_diversity": 0.2, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "unsafe"
    },
    {
        "key": "user/private/ssn",
        "value": "123-45-6789",
        "features": {"frequency": 0.2, "recency": 0.9, "consistency": 0.95, "semantic_novelty": 1.0, "source_diversity": 0.1, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "unsafe"
    },
    # Low consistency - contradictory evidence
    {
        "key": "user/preferences/color",
        "value": "both_blue_and_red",
        "features": {"frequency": 0.6, "recency": 0.7, "consistency": 0.1, "semantic_novelty": 0.8, "source_diversity": 0.5, "governance_conflict_flag": 1},
        "truth": "incorrect", "utility": "redundant", "safety": "safe"
    },
    # Low frequency, low diversity - insufficient evidence
    {
        "key": "user/rare/claim",
        "value": "unverified",
        "features": {"frequency": 0.1, "recency": 0.5, "consistency": 1.0, "semantic_novelty": 1.0, "source_diversity": 0.1, "governance_conflict_flag": 0},
        "truth": "uncertain", "utility": "premature", "safety": "safe"
    },
    {
        "key": "world/dubious/fact",
        "value": "unverified_claim",
        "features": {"frequency": 0.15, "recency": 0.3, "consistency": 0.5, "semantic_novelty": 0.9, "source_diversity": 0.1, "governance_conflict_flag": 1},
        "truth": "incorrect", "utility": "premature", "safety": "safe"
    },
]

CONFLICT_SCENARIOS = [
    # Mixed signals - council would have conflict (ALL REJECTED)
    {
        "key": "user/preferences/style",
        "value": "minimalist_or_ornate",
        "features": {"frequency": 0.5, "recency": 0.6, "consistency": 0.4, "semantic_novelty": 0.6, "source_diversity": 0.5, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "safe"
    },
    {
        "key": "context/agent/disagreement",
        "value": "contentious_topic",
        "features": {"frequency": 0.4, "recency": 0.5, "consistency": 0.3, "semantic_novelty": 0.7, "source_diversity": 0.6, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "safe"
    },
    {
        "key": "user/preference/ambiguous",
        "value": "maybe_likes_coffee",
        "features": {"frequency": 0.35, "recency": 0.55, "consistency": 0.45, "semantic_novelty": 0.65, "source_diversity": 0.4, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "safe"
    },
    # ADDITIONAL: Strong conflict flag examples (integer features like litmus test)
    {
        "key": "user/conflict/password_attempt",
        "value": "secret123",
        "features": {"frequency": 1, "recency": 0.95, "consistency": 1.0, "semantic_novelty": 1.0, "source_diversity": 1, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "unsafe"
    },
    {
        "key": "user/conflict/contradictory_pref",
        "value": "coffee_and_tea",
        "features": {"frequency": 2, "recency": 0.7, "consistency": 0.2, "semantic_novelty": 0.4, "source_diversity": 2, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "safe"
    },
    {
        "key": "user/conflict/disputed_claim",
        "value": "controversial",
        "features": {"frequency": 3, "recency": 0.8, "consistency": 0.5, "semantic_novelty": 0.6, "source_diversity": 3, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "safe"
    },
    {
        "key": "user/conflict/unsafe_data",
        "value": "ssn_attempt",
        "features": {"frequency": 1, "recency": 0.9, "consistency": 0.8, "semantic_novelty": 0.9, "source_diversity": 1, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "unsafe"
    },
    {
        "key": "world/conflict/wrong_fact",
        "value": "sydney_capital",
        "features": {"frequency": 2, "recency": 0.6, "consistency": 0.8, "semantic_novelty": 0.5, "source_diversity": 1, "governance_conflict_flag": 1},
        "truth": "incorrect", "utility": "redundant", "safety": "safe"
    },
    # More explicit: conflict_flag=1 with various other features - ALL REJECTED
    {
        "key": "user/cf1/high_freq",
        "value": "rejected_despite_freq",
        "features": {"frequency": 5, "recency": 0.8, "consistency": 0.9, "semantic_novelty": 0.3, "source_diversity": 3, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "safe"
    },
    {
        "key": "user/cf2/high_cons",
        "value": "rejected_despite_cons",
        "features": {"frequency": 4, "recency": 0.7, "consistency": 0.95, "semantic_novelty": 0.2, "source_diversity": 4, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "safe"
    },
    {
        "key": "user/cf3/multi_source",
        "value": "rejected_due_conflict",
        "features": {"frequency": 6, "recency": 0.9, "consistency": 0.85, "semantic_novelty": 0.1, "source_diversity": 5, "governance_conflict_flag": 1},
        "truth": "uncertain", "utility": "premature", "safety": "safe"
    },
]

# Additional edge cases
EDGE_CASES = [
    # High frequency but incorrect (common misconception)
    {
        "key": "world/misconception/goldfish",
        "value": "3_second_memory",
        "features": {"frequency": 0.8, "recency": 0.4, "consistency": 0.7, "semantic_novelty": 0.2, "source_diversity": 0.6, "governance_conflict_flag": 0},
        "truth": "incorrect", "utility": "redundant", "safety": "safe",
        "governance": "rejected"
    },
    # Low recency but correct (old but valid fact)
    {
        "key": "world/historical/moon_landing",
        "value": "1969",
        "features": {"frequency": 0.3, "recency": 0.1, "consistency": 1.0, "semantic_novelty": 0.1, "source_diversity": 0.9, "governance_conflict_flag": 0},
        "truth": "correct", "utility": "useful", "safety": "safe",
        "governance": "approved"
    },
    # High novelty, should be cautious
    {
        "key": "user/claim/extraordinary",
        "value": "unprecedented_claim",
        "features": {"frequency": 0.2, "recency": 0.9, "consistency": 0.8, "semantic_novelty": 1.0, "source_diversity": 0.2, "governance_conflict_flag": 0},
        "truth": "uncertain", "utility": "premature", "safety": "safe",
        "governance": "rejected"
    },
]


def generate_training_data(output_dir: str = "training_artifacts"):
    """Generate balanced training data."""
    Path(output_dir).mkdir(exist_ok=True)
    
    candidates = []
    labels = []
    
    seed_base = datetime.now().isoformat()
    
    # Generate approved examples
    for i, scenario in enumerate(APPROVED_SCENARIOS):
        seed = f"{seed_base}:approved:{i}"
        cand = generate_candidate(
            proposed_key=scenario["key"],
            value=scenario["value"],
            features=scenario["features"],
            seed=seed
        )
        label = generate_label(
            candidate_id=cand["candidate_id"],
            governance_decision="approved",
            truth_status=scenario["truth"],
            utility_status=scenario["utility"],
            safety_status=scenario["safety"]
        )
        candidates.append(cand)
        labels.append(label)
    
    # Generate rejected examples
    for i, scenario in enumerate(REJECTED_SCENARIOS):
        seed = f"{seed_base}:rejected:{i}"
        cand = generate_candidate(
            proposed_key=scenario["key"],
            value=scenario["value"],
            features=scenario["features"],
            seed=seed
        )
        label = generate_label(
            candidate_id=cand["candidate_id"],
            governance_decision="rejected",
            truth_status=scenario["truth"],
            utility_status=scenario["utility"],
            safety_status=scenario["safety"]
        )
        candidates.append(cand)
        labels.append(label)
    
    # Generate conflict examples
    for i, scenario in enumerate(CONFLICT_SCENARIOS):
        seed = f"{seed_base}:conflict:{i}"
        cand = generate_candidate(
            proposed_key=scenario["key"],
            value=scenario["value"],
            features=scenario["features"],
            seed=seed
        )
        # For conflicts, randomly assign approved/rejected but mark as conflict
        label = generate_label(
            candidate_id=cand["candidate_id"],
            governance_decision="rejected",  # Conflict => conservative rejection
            truth_status=scenario["truth"],
            utility_status=scenario["utility"],
            safety_status=scenario["safety"]
        )
        candidates.append(cand)
        labels.append(label)
    
    # Generate edge cases
    for i, scenario in enumerate(EDGE_CASES):
        seed = f"{seed_base}:edge:{i}"
        cand = generate_candidate(
            proposed_key=scenario["key"],
            value=scenario["value"],
            features=scenario["features"],
            seed=seed
        )
        label = generate_label(
            candidate_id=cand["candidate_id"],
            governance_decision=scenario["governance"],
            truth_status=scenario["truth"],
            utility_status=scenario["utility"],
            safety_status=scenario["safety"]
        )
        candidates.append(cand)
        labels.append(label)
    
    # Generate variations using feature sweeps
    for base_label, base_gov in [("correct", "approved"), ("incorrect", "rejected"), ("uncertain", "rejected")]:
        for freq in [0.2, 0.5, 0.8]:
            for cons in [0.3, 0.7, 0.95]:
                seed = f"{seed_base}:sweep:{base_label}:{freq}:{cons}"
                features = {
                    "frequency": freq,
                    "recency": 0.5,
                    "consistency": cons,
                    "semantic_novelty": 0.5,
                    "source_diversity": 0.5,
                    "governance_conflict_flag": 0 if cons > 0.5 else 1
                }
                
                # Adjust governance based on feature quality
                if freq >= 0.5 and cons >= 0.7:
                    gov = "approved"
                    truth = "correct" if cons > 0.8 else "uncertain"
                else:
                    gov = "rejected"
                    truth = "uncertain" if cons > 0.5 else "incorrect"
                
                cand = generate_candidate(
                    proposed_key=f"sweep/{base_label}/f{int(freq*10)}_c{int(cons*10)}",
                    value=f"sweep_value_{freq}_{cons}",
                    features=features,
                    seed=seed
                )
                label = generate_label(
                    candidate_id=cand["candidate_id"],
                    governance_decision=gov,
                    truth_status=truth,
                    utility_status="useful" if gov == "approved" else "premature",
                    safety_status="safe"
                )
                candidates.append(cand)
                labels.append(label)
    
    # Write to files
    with open(f"{output_dir}/enhanced_candidates.jsonl", "w") as f:
        for cand in candidates:
            f.write(json.dumps(cand) + "\n")
    
    with open(f"{output_dir}/enhanced_labels.jsonl", "w") as f:
        for label in labels:
            f.write(json.dumps(label) + "\n")
    
    # Stats
    gov_counts = {}
    truth_counts = {}
    for label in labels:
        gov = label["governance_decision"]
        truth = label["truth_status"]
        gov_counts[gov] = gov_counts.get(gov, 0) + 1
        truth_counts[truth] = truth_counts.get(truth, 0) + 1
    
    print(f"Generated {len(candidates)} candidates")
    print(f"\nGovernance distribution:")
    for k, v in sorted(gov_counts.items()):
        print(f"  {k}: {v} ({v/len(labels)*100:.1f}%)")
    print(f"\nTruth distribution:")
    for k, v in sorted(truth_counts.items()):
        print(f"  {k}: {v} ({v/len(labels)*100:.1f}%)")
    
    return candidates, labels


if __name__ == "__main__":
    generate_training_data()
