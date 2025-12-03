#!/usr/bin/env python3
"""
Security Validation Suite for Stage-1

Tests:
1. Invalid admin tokens rejected
2. Replay sandbox prevents SEM writes
3. Signature verification catches tampering

Usage:
    python tools/security_validation.py --db sqlite:///mace_stage1.db
"""
import argparse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from mace.governance import admin, killswitch
from mace.core import signing, persistence
from mace.runtime import executor

def test_invalid_token():
    """Test that invalid tokens are rejected."""
    print("Testing invalid token rejection...", end=" ")
    
    result = admin.verify_token("invalid_token_xyz")
    
    if result["valid"]:
        print("❌ FAIL - Invalid token accepted!")
        return False
    
    if result.get("reason") != "TOKEN_NOT_FOUND":
        print(f"❌ FAIL - Wrong error reason: {result.get('reason')}")
        return False
    
    print("✅ PASS")
    return True

def test_revoked_token():
    """Test that revoked tokens are rejected."""
    print("Testing revoked token rejection...", end=" ")
    
    # Generate token
    token, token_id = admin.generate_token("test", ttl_hours=1)
    
    # Revoke it
    admin.revoke_token(token_id)
    
    # Try to use
    result = admin.verify_token(token)
    
    if result["valid"]:
        print("❌ FAIL - Revoked token accepted!")
        return False
    
    if result.get("reason") != "TOKEN_REVOKED":
        print(f"❌ FAIL - Wrong error reason: {result.get('reason')}")
        return False
    
    print("✅ PASS")
    return True

def test_signature_tampering():
    """Test that modified payloads fail signature verification."""
    print("Testing signature tampering detection...", end=" ")
    
    payload = {"test": "data", "value": 42}
    signature = signing.sign_payload(payload, "test_key")
    
    # Tamper with payload
    payload["value"] = 99
    
    # Verify should fail
    if signing.verify_signature(payload, signature, "test_key"):
        print("❌ FAIL - Tampered payload verified!")
        return False
    
    print("✅ PASS")
    return True

def test_killswitch_blocks_execution():
    """Test that kill-switch blocks executor."""
    print("Testing kill-switch enforcement...", end=" ")
    
    # Activate kill-switch
    killswitch.activate("SECURITY_TEST", "validation_suite")
    
    # Try to execute
    try:
        executor.execute("test input", intent="test", log_enabled=False)
        print("❌ FAIL - Execution not blocked by kill-switch!")
        killswitch.deactivate()
        return False
    except RuntimeError as e:
        if "KILL_SWITCH_ACTIVE" not in str(e):
            print(f"❌ FAIL - Wrong exception: {e}")
            killswitch.deactivate()
            return False
    
    killswitch.deactivate()
    print("✅ PASS")
    return True

def run_all_tests(db_url):
    """Run all security validation tests."""
    if db_url:
        os.environ["MACE_DB_URL"] = db_url
    
    print("\n=== Security Validation Suite ===\n")
    
    tests = [
        test_invalid_token,
        test_revoked_token,
        test_signature_tampering,
        test_killswitch_blocks_execution
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
    parser = argparse.ArgumentParser(description="Run security validation suite")
    parser.add_argument("--db", help="Database URL")
    args = parser.parse_args()
    
    success = run_all_tests(args.db)
    sys.exit(0 if success else 1)
