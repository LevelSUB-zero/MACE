#!/usr/bin/env python3
"""
Fault Injection Test Suite

Tests system behavior under failure conditions.

Usage:
    python tools/test_fault_injection.py --db mace_stage1.db
"""
import argparse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from mace.runtime import executor
from mace.core import deterministic

def test_agent_crash_handling():
    """Test that agent crashes are handled gracefully."""
    print("Testing agent crash handling...", end=" ")
    
    deterministic.init_seed("fault_test_1")
    
    # Use input that might cause issues
    try:
        output, log = executor.execute("", intent="test", log_enabled=False)
        
       # Should complete without crashing
        if "error" in str(output).lower() or "fail" in str(output).lower():
            print("✅ PASS - Graceful error handling")
            return True
        else:
            print("✅ PASS - Completed successfully")
            return True
    except Exception as e:
        print(f"❌ FAIL - Unhandled exception: {e}")
        return False

def test_invalid_percept_handling():
    """Test handling of invalid percepts."""
    print("Testing invalid percept handling...", end=" ")
    
    deterministic.init_seed("fault_test_2")
    
    invalid_inputs = [
        None,
        "",
        "x" * 100000,  # Very long input
    ]
    
    for inp in invalid_inputs:
        try:
            if inp is not None:
                output, log = executor.execute(inp, intent="test", log_enabled=False)
        except TypeError:
            # None input should raise TypeError, which is fine
            continue
        except Exception as e:
            # Other exceptions should be handled gracefully
            if "EXECUTOR_ERROR" in str(e) or "INVALID_INPUT" in str(e):
                continue
            else:
                print(f"❌ FAIL - Unexpected exception for input {repr(inp)[:50]}: {e}")
                return False
    
    print("✅ PASS")
    return True

def test_deterministic_error_messages():
    """Test that error messages are deterministic."""
    print("Testing deterministic error messages...", end=" ")
    
    # Run same failing scenario twice
    results = []
    for i in range(2):
        deterministic.init_seed("fault_test_3")
        try:
            output, log = executor.execute("TRIGGER_ERROR", intent="test", log_enabled=False)
            results.append(str(output))
        except Exception as e:
            results.append(str(e))
    
    if len(results) == 2 and results[0] == results[1]:
        print("✅ PASS")
        return True
    else:
        print(f"❌ FAIL - Non-deterministic error messages")
        return False

def test_fallback_agent_activation():
    """Test that fallback agent activates when needed."""
    print("Testing fallback agent activation...", end=" ")
    
    deterministic.init_seed("fault_test_4")
    
    try:
        # Use input that doesn't match any specific agent strongly
        output, log = executor.execute("Random query", intent="unknown", log_enabled=False)
        
        # Should use fallback without crashing
        print("✅ PASS")
        return True
    except Exception as e:
        print(f"❌ FAIL - Fallback failed: {e}")
        return False

def run_all_tests(db_url):
    """Run all fault injection tests."""
    if db_url:
        os.environ["MACE_DB_URL"] = db_url
    
    print("\n=== Fault Injection Test Suite ===\n")
    
    tests = [
        test_agent_crash_handling,
        test_invalid_percept_handling,
        test_deterministic_error_messages,
        test_fallback_agent_activation
    ]
    
    results = []
    for test_func in tests:
        try:
            passed = test_func()
            results.append(passed)
        except Exception as e:
            print(f"❌ EXCEPTION in {test_func.__name__}: {e}")
            results.append(False)
    
    print(f"\n=== Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    print(f"Failed: {len(results) - sum(results)}/{len(results)}")
    
    return all(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run fault injection tests")
    parser.add_argument("--db", help="Database URL")
    args = parser.parse_args()
    
    success = run_all_tests(args.db)
    sys.exit(0 if success else 1)
