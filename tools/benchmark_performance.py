#!/usr/bin/env python3
"""
Performance Baseline Tool

Measures p50, p95, p99 latency for executor operations.

Usage:
    python tools/benchmark_performance.py --requests 100 --output perf_results.json
"""
import argparse
import json
import time
import sys
import os
from statistics import median, quantiles

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from mace.runtime import executor
from mace.core import deterministic

def run_performance_benchmark(num_requests, sample_input="Calculate 2+2"):
    """
    Run performance benchmark and collect latency metrics.
    
    Returns: dict with p50, p95, p99, mean, min, max latencies
    """
    latencies = []
    errors = 0
    
    print(f"Running {num_requests} requests...")
    
    for i in range(num_requests):
        seed = f"perf_test_{i}"
        deterministic.init_seed(seed)
        
        start = time.time()
        try:
            output, log_entry = executor.execute(sample_input, intent="test", seed=seed, log_enabled=False)
            elapsed = (time.time() - start) * 1000  # Convert to ms
            latencies.append(elapsed)
        except Exception as e:
            errors += 1
            print(f"Error in request {i}: {e}")
        
        if (i + 1) % 10 == 0:
            print(f"  Completed {i + 1}/{num_requests}...", file=sys.stderr)
    
    if not latencies:
        return {"error": "All requests failed"}
    
    # Calculate percentiles
    latencies.sort()
    n = len(latencies)
    
    results = {
        "total_requests": num_requests,
        "successful": len(latencies),
        "errors": errors,
        "latency_ms": {
            "min": min(latencies),
            "max": max(latencies),
            "mean": sum(latencies) / len(latencies),
            "p50": median(latencies),
            "p95": latencies[int(n * 0.95)] if n > 0 else 0,
            "p99": latencies[int(n * 0.99)] if n > 0 else 0,
        },
        "threshold_500ms": {
            "under": sum(1 for l in latencies if l < 500),
            "over": sum(1 for l in latencies if l >= 500),
            "percentage_under": sum(1 for l in latencies if l < 500) / len(latencies) * 100
        }
    }
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run performance baseline benchmark")
    parser.add_argument("--requests", type=int, default=100, help="Number of requests to run")
    parser.add_argument("--input", default="Calculate 2+2", help="Input text")
    parser.add_argument("--output", default="perf_results.json", help="Output file")
    
    args = parser.parse_args()
    
    results = run_performance_benchmark(args.requests, args.input)
    
    # Write results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"\n=== Performance Benchmark Results ===")
    print(f"Total requests: {results['total_requests']}")
    print(f"Successful: {results['successful']}")
    print(f"Errors: {results['errors']}")
    print(f"\nLatency (ms):")
    print(f"  p50: {results['latency_ms']['p50']:.2f}")
    print(f"  p95: {results['latency_ms']['p95']:.2f}")
    print(f"  p99: {results['latency_ms']['p99']:.2f}")
    print(f"  mean: {results['latency_ms']['mean']:.2f}")
    print(f"\nThreshold Analysis (< 500ms):")
    print(f"  Under threshold: {results['threshold_500ms']['percentage_under']:.1f}%")
    print(f"\nResults written to: {args.output}")
    
    # Exit code based on p95 threshold
    if results['latency_ms']['p95'] < 500:
        print(f"\n✅ PASS: p95 latency ({results['latency_ms']['p95']:.2f}ms) < 500ms")
        sys.exit(0)
    else:
        print(f"\n❌ FAIL: p95 latency ({results['latency_ms']['p95']:.2f}ms) >= 500ms")
        sys.exit(1)
