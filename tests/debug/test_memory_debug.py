"""
Debug script for Memory Storage and Recall
"""
import sys
import os
import time
sys.path.insert(0, os.path.abspath("src"))

from mace.memory import semantic, episodic, wm, cwm
from mace.core import deterministic

deterministic.init_seed("mem_debug_seed")

print("=== MEMORY DEBUG TEST ===")

# 1. Test Semantic Memory (Facts)
print("\n[1] Testing Semantic Memory (SEM)...")
key = "user/profile/user_123/debug_attr"
val = "debug_value_123"
print(f"Storing {key} = {val}...")
res = semantic.put_sem(key, val, source="debug_script")
if res["success"]:
    print("✓ Store success")
else:
    print(f"✗ Store failed: {res}")

print(f"Retrieving {key}...")
got = semantic.get_sem(key)
if got["exists"] and got["value"] == val:
    print(f"✓ Retrieve success: {got['value']}")
else:
    print(f"✗ Retrieve failed: {got}")


# 2. Test Episodic Memory (History)
print("\n[2] Testing Episodic Memory...")
ep = episodic.EpisodicMemory(job_seed="debug_job")
print("Recording interaction...")
ep.record_interaction(
    percept_text="debug percept",
    response_text="debug response",
    agent_id="debug_agent",
    metadata={"test": True}
)

print("Searching by summary 'debug'...")
# Give DB a moment?
time.sleep(0.1)
results = ep.search_by_summary("debug")
if results:
    print(f"✓ Found {len(results)} episodes")
    print(f"  First: {results[0]['summary']}")
else:
    print("✗ No episodes found")


# 3. Test Contextual Working Memory (CWM)
print("\n[3] Testing Contextual Working Memory (CWM)...")
c_mem = cwm.ContextualWorkingMemory(job_seed="debug_job")
print("Adding item to CWM...")
c_mem.add({"content": "cwm_debug_item"})

print("Retrieving recent items...")
items = c_mem.get_recent(5)
if items and any("cwm_debug_item" in i["content"] for i in items):
    print(f"✓ Found item in CWM: {items}")
else:
    print(f"✗ Item not found in CWM: {items}")

print("\n=== DEBUG COMPLETE ===")
