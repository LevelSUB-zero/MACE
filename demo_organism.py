"""
MACE: The Artificial Organism (Live Demo)
Visualization of the Observable Cognitive Space.
"""

import sys
import time
import json
from datetime import datetime

# Setup Path
sys.path.insert(0, r"f:\MAIN PROJECTS\Mace\src")

from mace.core.cognitive.cortex import ShadowCortex
from mace.core.cognitive.frame import CognitiveFrame

# Initialize the Brain
print("\n[INIT] Waking up the Shadow Cortex...")
cortex = ShadowCortex(job_seed="demo_session_v2")
print("[INIT] Organism Online. Mirror active. Reptile active.\n")

def print_separator(char="-"):
    print(char * 60)

def visualize_thought_loop(input_text: str, iterations: int = 1):
    print_separator("=")
    print(f" INPUT STIMULUS: '{input_text}'")
    print_separator("=")
    
    # Tick 1: Input Injection
    input_data = {"text": input_text, "content": input_text}
    _run_tick(input_data)
    
    # Subsequent Ticks: Pure Thought (No new input)
    for i in range(iterations - 1):
        time.sleep(0.5)
        _run_tick({})

def _run_tick(input_data):
    start_time = time.time()
    trace = cortex.process_active_thought(input_data)
    duration = (time.time() - start_time) * 1000
    
    # Visualize
    frame_data = trace["stage4_trace"]
    
    print(f"\n COGNITIVE FRAME (Tick {cortex.tick_counter})")
    print(f" |")
    
    if frame_data.get('action', {}).get('action_type') == 'reply' and 'Action Blocked' in str(frame_data):
         print(f" +-- [INHIBITION TRIGGERED]")
    
    print(f" +-- [REPTILE BRAIN] (Symbolic Logic)")
    print(f" |    +-- Op Proposal: {frame_data['op']}")
    
    # Determine Status
    op = frame_data['op']
    if op == "PLAN_GOAL":
        print(f" |    +-- Strategy: goal_formation")
    elif op == "VERIFY_LOGIC":
        print(f" |    +-- Strategy: internal_verification")
    elif op == "COMPLETE_GOAL":
        print(f" |    +-- Strategy: resolution")
        
    print(f" |")
    print(f" +-- [THE MIRROR] (Meta-Cognition)")
    awareness = frame_data["awareness"]
    if not awareness:
        print(f" |    +-- Status: DOMANT")
    else:
        for event in awareness:
             print(f" |    +-- [{event['type'].upper()}] {event['description']}")

    print(f" |")
    print(f" +-- [BROCA] (Action Layer)")
    action = frame_data["action"]
    print(f"      +-- Type: {action['action_type'].upper()}")
    print(f"      +-- Payload: {action['payload']}")
    
    print_separator()

# --- SCENARIO 3: Autonomous Reasoning ---
# We loop 3 times to see: PLAN_GOAL -> VERIFY_LOGIC -> COMPLETE_GOAL
visualize_thought_loop("Research quantum physics.", iterations=3)

# --- SCENARIO 2: Veto ---
# Should block immediately
time.sleep(1)
visualize_thought_loop("rm -rf all files", iterations=1)
