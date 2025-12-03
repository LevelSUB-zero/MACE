#!/usr/bin/env python3
"""
Replay Fidelity Benchmark for Stage-1

Tests deterministic execution by running executor with N seeds and verifying
that replay produces identical results.

Usage:
    python tools/run_replay_benchmark.py --seeds 1..100 --out replay_results.jsonl
"""
import argparse
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from mace.runtime import executor
from mace.replay import replay
from mace.core import deterministic, canonical

def run_benchmark(seed_range, sample_input, output_file):
    """
    Run replay benchmark across seed range.
    
    Args:
        seed_range: tuple (start, end) of seed numbers
        sample_input: text input for executor
        output_file: path to write results
    """
    start, end = seed_range
    results = []
    
    for seed_num in range(start, end + 1):
        seed = f"benchmark_seed_{seed_num}"
        
        # Run executor
        deterministic.init_seed(seed)
        try:
            output, log_entry = executor.execute(sample_input, intent="test", seed=seed, log_enabled=False)
        except Exception as e:
            results.append({
                "seed": seed,
                "seed_num": seed_num,
                "status": "EXECUTOR_ERROR",
                "error": str(e),
                "replay_match": False
            })
            continue
        
        # Replay
        try:
            replay_result = replay.replay_log(log_entry)
        except Exception as e:
            results.append({
                "seed": seed,
                "seed_num": seed_num,
                "status": "REPLAY_ERROR",
                "error": str(e),
                "replay_match": False
            })
            continue
        
        # Check match
        replay_match = replay_result.get("success", False)
        
        result = {
            "seed": seed,
            "seed_num": seed_num,
            "status": "OK" if replay_match else "MISMATCH",
            "replay_match": replay_match,
            "log_id": log_entry.get("log_id"),
            "final_output": log_entry.get("final_output", {}).get("text", "")
        }
        
        if not replay_match:
            result["error"] = replay_result.get("error")
            result["details"] = replay_result.get("details", "")
        
        results.append(result)
        
        # Progress
        if seed_num % 10 == 0:
            print(f"Processed {seed_num}/{end} seeds...", file=sys.stderr)
    
    # Write results
    with open(output_file, 'w') as f:
        for r in results:
            f.write(json.dumps(r) + '\n')
    
    # Summary
    total = len(results)
    matched = sum(1 for r in results if r["replay_match"])
    match_rate = (matched / total * 100) if total > 0 else 0
    
    print(f"\n=== Replay Benchmark Results ===", file=sys.stderr)
    print(f"Total seeds: {total}", file=sys.stderr)
    print(f"Matched: {matched}", file=sys.stderr)
    print(f"Mismatched: {total - matched}", file=sys.stderr)
    print(f"Match rate: {match_rate:.2f}%", file=sys.stderr)
    print(f"Results written to: {output_file}", file=sys.stderr)
    
    return match_rate == 100.0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run replay fidelity benchmark")
    parser.add_argument("--seeds", required=True, help="Seed range (e.g., 1..100)")
    parser.add_argument("--input", default="Calculate 2+2", help="Input text for executor")
    parser.add_argument("--out", default="replay_results.jsonl", help="Output file")
    
    args = parser.parse_args()
    
    # Parse seed range
    if ".." in args.seeds:
        start, end = map(int, args.seeds.split(".."))
    else:
        start = end = int(args.seeds)
    
    success = run_benchmark((start, end), args.input, args.out)
    sys.exit(0 if success else 1)
