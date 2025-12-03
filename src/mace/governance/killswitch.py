import os
import json

# Kill-switch state file (simple file-based flag for Stage-1)
KILLSWITCH_FILE = "mace_killswitch.flag"

def activate(reason="MANUAL_ACTIVATION", admin_id="unknown"):
    """
    Activate the kill-switch to halt all execution.
    """
    state = {
        "active": True,
        "reason": reason,
        "activated_by": admin_id,
        "activated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    }
    
    with open(KILLSWITCH_FILE, "w") as f:
        json.dump(state, f)
    
    return True

def is_active():
    """
    Check if kill-switch is currently active.
    """
    if not os.path.exists(KILLSWITCH_FILE):
        return False
        
    try:
        with open(KILLSWITCH_FILE, "r") as f:
            state = json.load(f)
        return state.get("active", False)
    except:
        return False

def deactivate(admin_id="unknown"):
    """
    Deactivate the kill-switch.
    Requires admin token validation (caller's responsibility).
    """
    if os.path.exists(KILLSWITCH_FILE):
        os.remove(KILLSWITCH_FILE)
    return True

def get_status():
    """
    Get current kill-switch status with details.
    """
    if not os.path.exists(KILLSWITCH_FILE):
        return {"active": False}
        
    try:
        with open(KILLSWITCH_FILE, "r") as f:
            return json.load(f)
    except:
        return {"active": False}
