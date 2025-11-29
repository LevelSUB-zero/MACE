import unittest
import json
import os
from mace.core import deterministic, telemetry
from mace.runtime import executor

class TestTelemetry(unittest.TestCase):
    
    def setUp(self):
        deterministic.init_seed("telemetry_test_seed")
        # Reset counters
        telemetry._apt_counters = {
            "total_calls": 0,
            "approved_count": 0,
            "rejected_count": 0,
            "total_latency_ms": 0
        }
        if os.path.exists("metrics/metrics.json"):
            os.remove("metrics/metrics.json")

    def test_8_1_apt_update_correctness(self):
        """
        8.1 — APT update correctness
        Run a pipeline. Check APT counters update.
        """
        # Run 1: Approved
        executor.execute("2+2", log_enabled=False)
        
        snapshot = telemetry.get_apt_snapshot()
        self.assertEqual(snapshot["total_calls"], 1)
        self.assertEqual(snapshot["approved_count"], 1)
        self.assertEqual(snapshot["rejected_count"], 0)
        self.assertEqual(snapshot["total_latency_ms"], 100) # Mocked 100ms
        
        # Run 2: Approved
        executor.execute("what is my favorite_color", log_enabled=False)
        
        snapshot = telemetry.get_apt_snapshot()
        self.assertEqual(snapshot["total_calls"], 2)
        self.assertEqual(snapshot["approved_count"], 2)
        
        print("\nPASS: APT update correctness")

    def test_8_2_metric_reporting(self):
        """
        8.2 — Metric reporting
        Check metrics.json contains required fields.
        """
        # Generate some data
        executor.execute("2+2", log_enabled=False)
        
        # Dump
        metrics = telemetry.dump_metrics("test_run")
        
        self.assertEqual(metrics["run_id"], "test_run")
        self.assertIn("apt", metrics)
        self.assertIn("derived", metrics)
        self.assertIn("avg_latency_ms", metrics["derived"])
        self.assertIn("repair_loop_frequency", metrics)
        self.assertIn("replay_determinism_rate", metrics)
        
        # Check file
        with open("metrics/metrics.json", "r") as f:
            loaded = json.load(f)
            self.assertEqual(loaded["run_id"], "test_run")
            
        print("PASS: Metric reporting")

if __name__ == "__main__":
    unittest.main()
