import copy
from mace.core import deterministic, canonical
from mace.config import config_loader

def create_snapshot(job_seed, initial_goals=None, resource_budget=None):
    """
    Initialize a new BrainState snapshot.
    """
    deterministic.init_seed(job_seed)
    
    if initial_goals is None:
        initial_goals = []
        
    snapshot = {
        "snapshot_id": deterministic.deterministic_id("brainstate_snapshot", "init"),
        "goals": initial_goals,
        "working_memory": [],
        "attention_gain": 1.0,
        "explore_bias": 0.5,
        "resource_load": {"cpu": 0.0, "memory": 0.0},
        "last_error": None,
        "tick_count": 0
    }
    return snapshot

def push_goal(brainstate, goal):
    """
    Add a goal to the stack.
    """
    brainstate["goals"].append(goal)
    
def pop_goal(brainstate):
    """
    Remove the last goal.
    """
    if brainstate["goals"]:
        return brainstate["goals"].pop()
    return None

def add_wm_item(brainstate, item):
    """
    Add an item to Working Memory.
    Item must be a dict with 'memory_id', 'content', etc.
    """
    # Enforce capacity
    max_wm = config_loader.get_wm_capacity()
    if len(brainstate["working_memory"]) >= max_wm:
        # Evict oldest or lowest priority?
        # For Stage-1, strict FIFO or priority?
        # Let's do simple FIFO for now, or remove one with lowest TTL?
        # Spec says "Strict TTL and promotion logic".
        # If full, maybe we just drop the oldest.
        brainstate["working_memory"].pop(0)
        
    # Add item with initial TTL
    ttl = config_loader.get_wm_ttl()
    item["ttl"] = ttl
    brainstate["working_memory"].append(item)

def tick(brainstate, events=None):
    """
    Advance the BrainState by one tick.
    - Decrement TTLs
    - Decay attention
    - Process events (optional)
    """
    brainstate["tick_count"] += 1
    
    # 1. Decay Attention
    decay_rate = config_loader.get_attention_decay_rate()
    brainstate["attention_gain"] *= decay_rate
    
    # 2. Update WM TTLs
    active_wm = []
    for item in brainstate["working_memory"]:
        item["ttl"] -= 1
        if item["ttl"] > 0:
            active_wm.append(item)
        else:
            # Expired -> Promote to CWM or Episodic?
            # For Stage-1, we just drop from WM. 
            # Promotion logic might be handled by a separate agent or process.
            # But the plan says "promotion logic (WM -> CWM -> Episodic)".
            # We'll just mark it as expired here.
            pass
            
    brainstate["working_memory"] = active_wm
    
    # 3. Update Snapshot ID
    # New ID depends on previous state + events
    # We need to canonicalize the state to hash it.
    # But we can't hash the ID itself if it's inside.
    # So we hash the content excluding ID.
    
    content_to_hash = copy.deepcopy(brainstate)
    if "snapshot_id" in content_to_hash:
        del content_to_hash["snapshot_id"]
        
    payload = canonical.canonical_json_serialize(content_to_hash)
    brainstate["snapshot_id"] = deterministic.deterministic_id("brainstate_snapshot", payload)
    
    return brainstate
