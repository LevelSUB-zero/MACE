import json
from mace.core import canonical

def encode(obj):
    """
    Encode object to canonical JSON string.
    """
    return canonical.canonical_json_serialize(obj)

def decode(json_str):
    """
    Decode JSON string to object.
    """
    return json.loads(json_str)
