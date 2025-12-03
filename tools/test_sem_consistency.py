#!/usr/bin/env python3
"""
SEM Consistency Test Suite

Tests semantic memory consistency under various conditions.

Usage:
    python tools/test_sem_consistency.py --db mace_stage1.db
"""
import argparse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from mace.memory import semantic
from mace.core import deterministic

def test_roundtrip_consistency():
    """Test PUT/GET roundtrip is deterministic."""
    print("Testing PUT/GET roundtrip consistency...", end=" ")
    
    deterministic.init_seed("sem_test_1")
    
    key = "test_key_123"
    value = {"data": "test_value", "num": 42}
    
    # PUT
    semantic.put(key, value)
    
    # GET
    retrieved = semantic.get(key)
    
    if retrieved != value:
        print(f"❌ FAIL - Retrieved value doesn't match")
        print(f"  Expected: {value}")
        print(f"  Got: {retrieved}")
        return False
    
    print("✅ PASS")
    return True

def test_pii_blocking():
    """Test that PII is blocked."""
    print("Testing PII blocking...", end=" ")
    
    deterministic.init_seed("sem_test_2")
    
    # Try to store PII
    key = "user_data"
    pii_value = {"email": "test@example.com", "ssn": "123-45-6789"}
    
    result = semantic.put(key, pii_value)
    
    # Check if blocked
    if result == "PRIVACY_BLOCKED":
        print("✅ PASS")
        return True
    else:
        print(f"❌ FAIL - PII not blocked, result: {result}")
        return False

def test_max_size_enforcement():
    """Test that oversized values are rejected."""
    print("Testing max size enforcement...", end=" ")
    
    deterministic.init_seed("sem_test_3")
    
    key = "large_data"
    # Create value larger than MAX_EVIDENCE_SIZE (16KB)
    large_value = {"data": "x" * 20000}
    
    result = semantic.put(key, large_value)
    
    if "ERROR" in str(result) or result == "SIZE_EXCEEDED":
        print("✅ PASS")
        return True
    else:
        print(f"❌ FAIL - Oversized value accepted")
        return False

def test_deterministic_retrieval():
    """Test that multiple retrievals are deterministic."""
    print("Testing deterministic retrieval...", end=" ")
    
    deterministic.init_seed("sem_test_4")
    
    key = "deterministic_key"
    value = {"count": 123, "state": "active"}
    
    semantic.put(key, value)
    
    # Retrieve multiple times
    results = [semantic.get(key) for _ in range(5)]
    
    # All should be identical
    if all(r == results[0] for r in results):
        print("✅ PASS")
        return True
    else:
        print("❌ FAIL - Non-deterministic retrieval")
        return False

def run_all_tests(db_url):
    """Run all SEM consistency tests."""
    if db_url:
        os.environ["MACE_DB_URL"] = db_url
    
    print("\n=== SEM Consistency Test Suite ===\n")
    
    tests = [
        test_roundtrip_consistency,
        test_pii_blocking,
        test_max_size_enforcement,
        test_deterministic_retrieval
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
    parser = argparse.ArgumentParser(description="Run SEM consistency tests")
    parser.add_argument("--db", help="Database URL")
    args = parser.parse_args()
    
    success = run_all_tests(args.db)
    sys.exit(0 if success else 1)
