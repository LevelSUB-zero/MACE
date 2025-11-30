import json
import os
from collections import defaultdict

METRICS_FILE = "logs/metrics.json"

class MetricsRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsRegistry, cls).__new__(cls)
            cls._instance.counters = defaultdict(int)
        return cls._instance

    def increment(self, name, value=1):
        self.counters[name] += value
        
    def get(self, name):
        return self.counters[name]
        
    def save(self):
        """Save metrics to file."""
        os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
        with open(METRICS_FILE, "w") as f:
            json.dump(self.counters, f, indent=2)
            
    def reset(self):
        self.counters = defaultdict(int)

# Global helper
def increment(name, value=1):
    MetricsRegistry().increment(name, value)

def save():
    MetricsRegistry().save()
