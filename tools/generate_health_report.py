import unittest
import json
import os
import time
import sys

# Ensure src is in path
sys.path.append(os.path.abspath("src"))

REPORT_FILE = "reports/health_report.json"

class HealthCheckResult(unittest.TestResult):
    def __init__(self, stream=None, descriptions=None, verbosity=None):
        super(HealthCheckResult, self).__init__(stream, descriptions, verbosity)
        self.successes = []
        self.failures_list = []
        self.errors_list = []

    def addSuccess(self, test):
        super(HealthCheckResult, self).addSuccess(test)
        self.successes.append(test)

    def addFailure(self, test, err):
        super(HealthCheckResult, self).addFailure(test, err)
        self.failures_list.append((test, err))

    def addError(self, test, err):
        super(HealthCheckResult, self).addError(test, err)
        self.errors_list.append((test, err))

def run_health_check():
    loader = unittest.TestLoader()
    suite = loader.discover("tests/health_check")
    
    result = HealthCheckResult()
    suite.run(result)
    
    # Generate Report
    report = {
        "run_id": f"health-{int(time.time())}",
        "timestamp": time.time(),
        "summary": {
            "overall_status": "PASS" if result.wasSuccessful() else "FAIL",
            "total_tests": result.testsRun,
            "passed": len(result.successes),
            "failed": len(result.failures_list),
            "errors": len(result.errors_list)
        },
        "failures": [],
        "artifacts": {
            "reports": [REPORT_FILE],
            "metrics": "metrics/metrics.json"
        }
    }
    
    for test, err in result.failures_list:
        report["failures"].append({
            "test_id": str(test),
            "message": str(err[1]),
            "type": "FAILURE"
        })
        
    for test, err in result.errors_list:
        report["failures"].append({
            "test_id": str(test),
            "message": str(err[1]),
            "type": "ERROR"
        })
        
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
        
    print(json.dumps(report, indent=2))
    
    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == "__main__":
    run_health_check()
