"""
Debug script for Stage-1 Router
"""
import sys
import os
sys.path.insert(0, os.path.abspath("src"))

from mace.router import stage1_router
from mace.core.intent_parser import parse_intent

# Mock available agents
agents = [
    {"module_id": "mace.agents.math_agent"},
    {"module_id": "mace.agents.profile_agent"},
    {"module_id": "mace.agents.knowledge_agent"},
    {"module_id": "mace.agents.generic_agent"},
]

brainstate = {}

tests = [
    "calculate 2 + 2",
    "my name is Bob",
    "who is Bob",
    "what is gravity",
    "hello",
    "foobar",
]

print("Testing Router...")
for t in tests:
    try:
        percept = {"text": t}
        decision = stage1_router.route(percept, brainstate, agents)
        agent_id = decision['selected_agents'][0]['agent_id']
        print(f"'{t}' -> {agent_id} (Reason: {decision['reasoning']})")
    except Exception as e:
        print(f"ERROR '{t}': {e}")
        import traceback
        traceback.print_exc()
