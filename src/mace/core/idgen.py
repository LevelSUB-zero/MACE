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

    return deterministic.deterministic_id(namespace, payload, counter)
