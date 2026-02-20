#!/usr/bin/env python3
"""
Time-Shifted Replay Runner

Replay candidates against different historical SEM states.
Teaches MEM-SNN temporal reasoning.

Time points:
- T0: Empty SEM (cold start)
- T1: Partial SEM (some existing facts)
- T2: Dense SEM (many existing facts)
"""
import os
import sys
import json
import copy
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from mace.core import deterministic
from mace.memory import consolidator, rewards


# =============================================================================
# SEM State Snapshots (Simulated Historical States)
# =============================================================================

SEM_SNAPSHOTS = {
    "T0_empty": {
        "description": "Cold start - no existing facts",
        "tick": 0,
        "state": {}
    },
    "T1_partial": {
        "description": "Partial population - some basics",
        "tick": 5,
        "state": {
            "user/profile/name": "alice",
            "user/settings/theme": "dark",
            "world/fact/geography/capital_australia": "canberra",
        }
    },
    "T2_dense": {
        "description": "Dense population - many existing facts",
        "tick": 12,
        "state": {
            "user/profile/name": "alice",
            "user/profile/role": "developer",
            "user/preferences/language": "python",
            "user/settings/theme": "dark",
            "user/settings/notifications": "enabled",
            "world/fact/geography/capital_australia": "canberra",
            "world/fact/geography/capital_france": "paris",
            "world/fact/geography/capital_japan": "tokyo",
            "world/fact/math/ohms_law": "v=ir",
            "world/fact/science/water_formula": "h2o",
            "context/project/name": "mace",
            "context/project/language": "python",
        }
    }
}


def run_time_shifted_replay(
    candidates: List[Dict],
    snapshot_name: str,
    snapshot_data: Dict
) -> Dict:
    """
    Run replay against a specific SEM snapshot.
    """
    sem_state = snapshot_data["state"]
    current_tick = snapshot_data["tick"]
    
    labels = []
    status_counts = {"useful": 0, "redundant": 0, "premature": 0}
    
    for candidate in candidates:
        # Compute labels with this SEM state
        label = rewards.compute_full_label(
            candidate, current_tick, sem_state,
            "approved"  # Assume all approved for replay analysis
        )
        label["snapshot"] = snapshot_name
        label["snapshot_tick"] = current_tick
        labels.append(label)
        
        status_counts[label["utility_status"]] += 1
    
    return {
        "snapshot_name": snapshot_name,
        "description": snapshot_data["description"],
        "tick": current_tick,
        "sem_size": len(sem_state),
        "labels": labels,
        "stats": status_counts,
    }


def run_all_time_shifts(
    candidates: List[Dict],
    output_dir: str = "training_artifacts/time_shifts"
) -> List[Dict]:
    """
    Run all time-shifted replays.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    all_results = []
    
    for snap_name, snap_data in SEM_SNAPSHOTS.items():
        print(f"\n=== Running time-shift: {snap_name} ===")
        print(f"  Description: {snap_data['description']}")
        print(f"  SEM size: {len(snap_data['state'])} items")
        
        result = run_time_shifted_replay(candidates, snap_name, snap_data)
        
        print(f"  Stats: {result['stats']}")
        all_results.append(result)
        
        # Save results
        with open(f"{output_dir}/{snap_name}_labels.jsonl", "w") as f:
            for l in result["labels"]:
                f.write(json.dumps(l) + "\n")
    
    # Analyze temporal patterns
    temporal_analysis = analyze_temporal_patterns(all_results, candidates)
    
    # Save summary
    summary = {
        "sweep_type": "time_shifted",
        "snapshots": [r["snapshot_name"] for r in all_results],
        "stats": {r["snapshot_name"]: r["stats"] for r in all_results},
        "temporal_analysis": temporal_analysis,
    }
    with open(f"{output_dir}/time_shift_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n=== Time-Shift Complete ===")
    print(f"  Snapshots: {len(all_results)}")
    for r in all_results:
        print(f"    {r['snapshot_name']}: {r['stats']}")
    
    return all_results


def analyze_temporal_patterns(
    results: List[Dict],
    candidates: List[Dict]
) -> Dict:
    """
    Analyze how candidate status changes across time.
    """
    # Map candidate_id -> {snapshot: status}
    status_map = {}
    for candidate in candidates:
        cid = candidate["candidate_id"]
        status_map[cid] = {
            "candidate": candidate,
            "by_time": {}
        }
    
    for result in results:
        snap = result["snapshot_name"]
        for label in result["labels"]:
            cid = label["candidate_id"]
            if cid in status_map:
                status_map[cid]["by_time"][snap] = label["utility_status"]
    
    # Classify patterns
    patterns = {
        "always_useful": [],
        "becomes_redundant": [],
        "never_escapes_premature": [],
        "variable": [],
    }
    
    for cid, data in status_map.items():
        statuses = list(data["by_time"].values())
        
        if all(s == "useful" for s in statuses):
            patterns["always_useful"].append(cid)
        elif "redundant" in statuses and statuses[0] != "redundant":
            patterns["becomes_redundant"].append(cid)
        elif all(s == "premature" for s in statuses):
            patterns["never_escapes_premature"].append(cid)
        else:
            patterns["variable"].append(cid)
    
    return {
        "pattern_counts": {k: len(v) for k, v in patterns.items()},
        "examples": {
            k: v[:3] for k, v in patterns.items()  # First 3 examples
        }
    }


if __name__ == "__main__":
    print("Time-Shifted Replay Runner")
    print("Usage: python sweep_time_shift.py")
    print("(Requires candidates to be loaded first)")
