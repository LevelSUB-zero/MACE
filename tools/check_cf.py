#!/usr/bin/env python3
"""Check conflict flag training examples."""
import json

with open('training_artifacts/enhanced_candidates.jsonl') as f:
    cands = [json.loads(l) for l in f if l.strip()]
with open('training_artifacts/enhanced_labels.jsonl') as f:
    labels = [json.loads(l) for l in f if l.strip()]

label_map = {l['candidate_id']: l for l in labels}

print('Examples with governance_conflict_flag=1:')
cf1_count = 0
for c in cands:
    if c['features'].get('governance_conflict_flag', 0) == 1:
        cf1_count += 1
        cid = c['candidate_id']
        label = label_map.get(cid, {})
        gov = label.get('governance_decision', 'MISSING')
        freq = c['features'].get('frequency', '?')
        cons = c['features'].get('consistency', '?')
        print(f"  freq={freq} cons={cons} -> {gov}")

print(f"\nTotal cf=1 examples: {cf1_count}")
print(f"Total examples: {len(cands)}")
