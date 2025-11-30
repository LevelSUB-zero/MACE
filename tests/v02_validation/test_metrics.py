import unittest
import os
import json
from mace.ops import metrics
from mace.runtime import executor
from mace.memory import semantic
from mace.core import deterministic

class TestMetrics(unittest.TestCase):
    def setUp(self):
        metrics.MetricsRegistry().reset()
        deterministic.set_mode("DETERMINISTIC")
        deterministic.init_seed("metrics_test_seed")
        
        # Cleanup
        if os.path.exists("logs/metrics.json"):
            os.remove("logs/metrics.json")
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")

    def tearDown(self):
        if os.path.exists("logs/metrics.json"):
            os.remove("logs/metrics.json")
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")

    def test_metrics_collection(self):
        """Verify metrics are incremented."""
        # 1. Run executor (should increment agent_executions, logs_written)
        executor.execute("2 + 2")
        
        reg = metrics.MetricsRegistry()
        self.assertEqual(reg.get("agent_executions_total"), 1)
        self.assertEqual(reg.get("reflective_logs_written_total"), 1)
        
        # 2. Run SEM write (should increment sem_writes)
        semantic.put_sem("user/profile/test/key", "val")
        self.assertEqual(reg.get("sem_writes_total"), 1)
        
        # 3. Run SEM read (should increment sem_reads)
        semantic.get_sem("user/profile/test/key")
        self.assertEqual(reg.get("sem_reads_total"), 1)

    def test_metrics_persistence(self):
        """Verify metrics are saved to file."""
        metrics.increment("test_metric", 5)
        metrics.save()
        
        self.assertTrue(os.path.exists("logs/metrics.json"))
        with open("logs/metrics.json", "r") as f:
            data = json.load(f)
            self.assertEqual(data["test_metric"], 5)

if __name__ == '__main__':
    unittest.main()
