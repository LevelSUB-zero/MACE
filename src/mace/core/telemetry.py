import json
import os
import time

# Global counters
_apt_counters = {
    "total_calls": 0,
    "approved_count": 0,
    "rejected_count": 0,
    "total_latency_ms": 0
}

METRICS_FILE = "metrics/metrics.json"

def update_apt(approved, latency_ms):
    global _apt_counters
    _apt_counters["total_calls"] += 1
    if approved:
        _apt_counters["approved_count"] += 1
    else:
        _apt_counters["rejected_count"] += 1
    _apt_counters["total_latency_ms"] += latency_ms

def get_apt_snapshot():
    return _apt_counters.copy()

def dump_metrics(run_id="default"):
    """
    Dump metrics to JSON file.
    """
    os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
    
    avg_latency = 0
    if _apt_counters["total_calls"] > 0:
        avg_latency = _apt_counters["total_latency_ms"] / _apt_counters["total_calls"]
        
    metrics = {
        "run_id": run_id,
        "timestamp": time.time(), # Real time for metrics is fine? Or deterministic?
        # Telemetry usually needs real time.
        "apt": _apt_counters,
        "derived": {
            "avg_latency_ms": avg_latency,
            "approval_rate": _apt_counters["approved_count"] / _apt_counters["total_calls"] if _apt_counters["total_calls"] > 0 else 0
        },
        "repair_loop_frequency": 0, # Placeholder
        "average_repair_iterations": 0, # Placeholder
        "replay_determinism_rate": 1.0 # Placeholder
    }
    
    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f, indent=2)
        
    return metrics
