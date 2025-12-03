#!/usr/bin/env python3
"""
Analyze Replay Benchmark Results

Parses replay_results.jsonl and produces detailed mismatch analysis.

Usage:
    python tools/analyze_replay_results.py replay_results.jsonl
"""
import json
import sys
from collections import Counter

def analyze_results(results_file):
    """
    Analyze replay benchmark results and report mismatches.
    
    Returns: True if all matched, False otherwise
    """
    results = []
    with open(results_file, 'r') as f:
        for line in f:
            results.append(json.loads(line))
    
    total = len(results)
    matched = [r for r in results if r["replay_match"]]
    mismatched = [r for r in results if not r["replay_match"]]
    
    print(f"=== Replay Analysis ===")
    print(f"Total: {total}")
    print(f"Matched: {len(matched)} ({len(matched)/total*100:.1f}%)")
    print(f"Mismatched: {len(mismatched)} ({len(mismatched)/total*100:.1f}%)")
    print()
    
    if not mismatched:
        print("✅ ALL REPLAYS MATCHED - 100% fidelity")
        return True
    
    # Analyze mismatch patterns
    print("❌ MISMATCHES DETECTED")
    print(f"\nTop {min(10, len(mismatched))} Mismatches:")
    print("-" * 80)
    
    error_types = Counter(r.get("error", "UNKNOWN") for r in mismatched)
    
    for i, result in enumerate(mismatched[:10], 1):
        print(f"\n{i}. Seed: {result['seed']}")
        print(f"   Error: {result.get('error', 'UNKNOWN')}")
        if "details" in result and result["details"]:
            details = result["details"][:200]  # Truncate long details
            print(f"   Details: {details}")
        print(f"   Log ID: {result.get('log_id', 'N/A')}")
    
    print(f"\n\nError Distribution:")
    for error, count in error_types.most_common():
        print(f"  {error}: {count}")
    
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_replay_results.py <results_file.jsonl>")
        sys.exit(1)
    
    success = analyze_results(sys.argv[1])
    sys.exit(0 if success else 1)
