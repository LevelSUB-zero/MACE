#!/usr/bin/env python3
"""
Extract Training Artifacts for MEM-SNN

Extracts LR-01 test data into the required folder structure:

training_artifacts/
├── candidates.jsonl
├── labels.jsonl
├── outcomes.jsonl
├── snapshots/
│   ├── selfrep_snapshot.json
│   ├── brainstate_snapshot.json
└── README.md

Usage:
    python tools/extract_training_artifacts.py --output training_artifacts/
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from mace.core import persistence
from mace.memory import consolidator
from mace.governance import admin
from mace.self_representation import core as selfrep
from mace.brainstate import brainstate, persistence as bs_persistence


def extract_candidates(output_dir: str) -> int:
    """Extract MEMCandidates to candidates.jsonl"""
    candidates = consolidator.get_all_candidates()
    
    output_path = os.path.join(output_dir, "candidates.jsonl")
    with open(output_path, "w") as f:
        for candidate in candidates:
            f.write(json.dumps(candidate) + "\n")
    
    print(f"  ✓ Extracted {len(candidates)} candidates to candidates.jsonl")
    return len(candidates)


def extract_labels(output_dir: str) -> int:
    """Extract governance decisions to labels.jsonl"""
    decisions = admin.get_governance_decisions()
    
    output_path = os.path.join(output_dir, "labels.jsonl")
    with open(output_path, "w") as f:
        for decision in decisions:
            label = {
                "candidate_id": decision["candidate_id"],
                "label": decision["decision"],
                "reason": decision["reason"],
                "heuristic_would_approve": decision.get("heuristic_would_approve")
            }
            f.write(json.dumps(label) + "\n")
    
    print(f"  ✓ Extracted {len(decisions)} labels to labels.jsonl")
    return len(decisions)


def extract_outcomes(output_dir: str) -> int:
    """Extract outcome measurements to outcomes.jsonl"""
    outcomes = admin.get_outcome_measurements()
    
    # Group by candidate_id to create before/after pairs
    by_candidate = {}
    for outcome in outcomes:
        cid = outcome["candidate_id"]
        if cid not in by_candidate:
            by_candidate[cid] = {"before": None, "after": None}
        
        if outcome["phase"] == "baseline":
            by_candidate[cid]["before"] = outcome["metrics"]
        elif outcome["phase"] == "post_promotion":
            by_candidate[cid]["after"] = outcome["metrics"]
    
    output_path = os.path.join(output_dir, "outcomes.jsonl")
    count = 0
    with open(output_path, "w") as f:
        for cid, data in by_candidate.items():
            if data["before"] and data["after"]:
                entry = {
                    "candidate_id": cid,
                    "before": data["before"],
                    "after": data["after"]
                }
                f.write(json.dumps(entry) + "\n")
                count += 1
    
    print(f"  ✓ Extracted {count} outcome pairs to outcomes.jsonl")
    return count


def extract_snapshots(output_dir: str):
    """Extract system snapshots"""
    snapshots_dir = os.path.join(output_dir, "snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)
    
    # Self-representation snapshot
    try:
        selfrep_snapshot = selfrep.graph_snapshot()
        with open(os.path.join(snapshots_dir, "selfrep_snapshot.json"), "w") as f:
            json.dump(selfrep_snapshot, f, indent=2)
        print("  ✓ Extracted selfrep_snapshot.json")
    except Exception as e:
        print(f"  ⚠ Could not extract selfrep: {e}")
        with open(os.path.join(snapshots_dir, "selfrep_snapshot.json"), "w") as f:
            json.dump({"nodes": [], "edges": [], "error": str(e)}, f, indent=2)
    
    # BrainState snapshot
    try:
        bs = bs_persistence.load_latest_snapshot("lr01_test_master_seed")
        if bs:
            with open(os.path.join(snapshots_dir, "brainstate_snapshot.json"), "w") as f:
                json.dump(bs, f, indent=2)
            print("  ✓ Extracted brainstate_snapshot.json")
        else:
            with open(os.path.join(snapshots_dir, "brainstate_snapshot.json"), "w") as f:
                json.dump({"goals": [], "working_memory": [], "tick": 0}, f, indent=2)
            print("  ⚠ No brainstate found, created empty snapshot")
    except Exception as e:
        print(f"  ⚠ Could not extract brainstate: {e}")
        with open(os.path.join(snapshots_dir, "brainstate_snapshot.json"), "w") as f:
            json.dump({"goals": [], "working_memory": [], "tick": 0, "error": str(e)}, f, indent=2)


def create_readme(output_dir: str, stats: dict):
    """Create README.md for the training artifacts"""
    readme = f"""# LR-01 Training Artifacts

Generated: {datetime.now().isoformat()}

## Contents

- `candidates.jsonl` - {stats['candidates']} MEMCandidate objects
- `labels.jsonl` - {stats['labels']} governance labels (approve/reject)
- `outcomes.jsonl` - {stats['outcomes']} outcome measurement pairs
- `snapshots/` - System state snapshots

## Schema

### candidates.jsonl
```json
{{
  "candidate_id": "string",
  "features": {{
    "frequency": 0.0-1.0,
    "recency": 0.0-1.0,
    "consistency": 0.0-1.0,
    "semantic_novelty": 0.0-1.0,
    "source_diversity": 0.0-1.0,
    "governance_conflict_flag": boolean
  }},
  "proposed_key": "string",
  "value": "string",
  "provenance": ["episodic_id", ...],
  "consolidator_score": 0.0-1.0,
  "mem_snn_score": 0.0-1.0
}}
```

### labels.jsonl
```json
{{
  "candidate_id": "string",
  "label": "approve|reject",
  "reason": "string"
}}
```

### outcomes.jsonl
```json
{{
  "candidate_id": "string",
  "before": {{"repair_loops": N, "fallback_count": N, "confidence": 0.0-1.0, "latency_class": "string"}},
  "after": {{"repair_loops": N, "fallback_count": N, "confidence": 0.0-1.0, "latency_class": "string"}}
}}
```

## Usage

Load for MEM-SNN training:

```python
import json

candidates = [json.loads(line) for line in open('candidates.jsonl')]
labels = [json.loads(line) for line in open('labels.jsonl')]
outcomes = [json.loads(line) for line in open('outcomes.jsonl')]

# Join by candidate_id
training_data = []
for c in candidates:
    label = next((l for l in labels if l['candidate_id'] == c['candidate_id']), None)
    outcome = next((o for o in outcomes if o['candidate_id'] == c['candidate_id']), None)
    
    training_data.append({{
        'features': c['features'],
        'label': label['label'] if label else None,
        'outcome': outcome
    }})
```
"""
    
    with open(os.path.join(output_dir, "README.md"), "w") as f:
        f.write(readme)
    
    print("  ✓ Created README.md")


def main():
    parser = argparse.ArgumentParser(description="Extract LR-01 training artifacts")
    parser.add_argument("--output", "-o", default="training_artifacts",
                        help="Output directory (default: training_artifacts)")
    parser.add_argument("--db", default=None,
                        help="Database path (default: uses MACE_DB_URL)")
    
    args = parser.parse_args()
    
    # Set DB if provided
    if args.db:
        os.environ["MACE_DB_URL"] = f"sqlite:///{args.db}"
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    print("="*60)
    print("Extracting LR-01 Training Artifacts")
    print("="*60)
    print(f"Output: {args.output}")
    print()
    
    # Extract all components
    stats = {}
    stats['candidates'] = extract_candidates(args.output)
    stats['labels'] = extract_labels(args.output)
    stats['outcomes'] = extract_outcomes(args.output)
    extract_snapshots(args.output)
    create_readme(args.output, stats)
    
    print()
    print("="*60)
    print("✅ Extraction Complete")
    print("="*60)
    print(f"Total candidates: {stats['candidates']}")
    print(f"Total labels: {stats['labels']}")
    print(f"Total outcomes: {stats['outcomes']}")


if __name__ == "__main__":
    main()
