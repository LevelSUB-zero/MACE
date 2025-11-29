import hmac
import hashlib
from mace.core import deterministic

def deterministic_id(namespace, payload, counter=None):
    """
    Generate a deterministic ID using HMAC-SHA256.
    
    Format: hex digest of HMAC(seed, namespace || payload || counter)
    
    Args:
        namespace (str): The scope of the ID (e.g., "percept", "vote").
        payload (str): The content to hash (e.g., text, agent_id).
        counter (int, optional): A counter to ensure uniqueness. 
                                 If None, uses global ID counter.
    """
    seed = deterministic.get_seed()
    if seed is None:
        # If no seed set, and we are in NORMAL mode, we could use random, 
        # but spec says "deterministic_id" so we should probably enforce seed or use a default if allowed.
        # Rulebook says: "deterministic_id = HMAC_SHA256(seed || namespace || payload || counter)"
        # Implies seed is required.
        if deterministic.get_mode() == "NORMAL":
             # Fallback for normal mode if seed not set? Or just raise?
             # Let's auto-init a default seed if none exists in NORMAL mode for convenience,
             # but strictly raise in DETERMINISTIC mode.
             seed = "default_unsafe_seed"
        else:
             raise RuntimeError("Seed not initialized for deterministic_id.")

    if counter is None:
        counter = deterministic.increment_counter("id")

    # Construct message
    # Separator '||' used in concept, here we just concat with a delimiter
    message = f"{namespace}:{payload}:{counter}".encode('utf-8')
    key = seed.encode('utf-8')
    
    # HMAC
    h = hmac.new(key, message, hashlib.sha256)
    return h.hexdigest()
