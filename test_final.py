"""Final test of dynamic KG tagging via executor"""
from mace.runtime import executor
from mace.memory.episodic import EpisodicMemory
from mace.memory.knowledge_graph import get_knowledge_graph
from mace.core import deterministic
import os

# Clean state
for db in ["mace_stage1.db", "mace_memory.db"]:
    if os.path.exists(db):
        os.remove(db)

deterministic.init_seed('final_kg_test')

print("=== Running interactions ===\n")

# Store user info
r1, _ = executor.execute('remember my name is Alice')
print(f"1: {r1['text']}")

# Store friend info
r2, _ = executor.execute("my friend's name is John")
print(f"2: {r2['text']}")

# Add info about John
r3, _ = executor.execute("John is a footballer")
print(f"3: {r3['text']}")

# Check episodic tags
print("\n=== Episodic Memory (with KG tags) ===")
ep = EpisodicMemory()
for r in ep.get_recent(5):
    print(f"Summary: {r['summary']}")
    print(f"Tags: {r['payload'].get('context_tags', [])}")
    print()

# Check Knowledge Graph
print("=== Knowledge Graph ===")
kg = get_knowledge_graph()

print("\nUser entity:")
info = kg.recall_about("user")
print(f"  Attributes: {info.get('attributes', {})}")

print("\nJohn entity:")
info = kg.recall_about("john")
print(f"  Attributes: {info.get('attributes', {})}")
print(f"  Relations: {info.get('relations', [])}")
