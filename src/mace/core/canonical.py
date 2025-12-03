import json
import unicodedata
import re

def canonical_float_format(f):
    """
    Format a float to exactly 9 decimal places.
    """
    if isinstance(f, (int, float)):
        return "{:.9f}".format(f)
    return str(f)

def canonical_json_serialize(obj):
    """
    Serialize object to JSON with deterministic ordering, no whitespace, 
    NFKD normalization, and 9-decimal floats.
    """
    # Recursive helper to normalize strings and floats
    def normalize(o):
        if isinstance(o, dict):
            return {k: normalize(v) for k, v in o.items()}
        elif isinstance(o, list):
            return [normalize(v) for v in o]
        elif isinstance(o, str):
            return unicodedata.normalize('NFKD', o)
        elif isinstance(o, float):
            # We want to serialize floats as strings with fixed precision 
            # to avoid platform differences in float representation?
            # Or just ensure the JSON serializer handles them consistently?
            # The spec says "canonical float 9 decimals".
            # Standard json.dumps might vary. 
            # Let's convert to string for strict canonicalization if it's for hashing.
            # But if it's for the JSON payload itself, we might want to keep it as number 
            # but ensure it's written with 9 decimals.
            # Python's json module doesn't easily allow forcing decimal places for numbers 
            # without converting to string or using a custom encoder that outputs raw json.
            # For now, let's assume we convert to string representation if it's for hashing/signing.
            # If it's for the actual log payload, we might keep it as float.
            # However, for "canonical_json_serialize" which is likely used for signing/hashing,
            # string conversion is safer.
            return float("{:.9f}".format(o)) 
        return o

    normalized_obj = normalize(obj)
    
    # separators=(',', ':') removes whitespace
    # sort_keys=True ensures deterministic order
    # ensure_ascii=False allows unicode characters (which we normalized)
    return json.dumps(normalized_obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def canonical_key(raw_key):
    """
    Generate a canonical key from a raw string.
    Rules: Lowercase, replace spaces with underscores, remove non-alphanumeric (except allowed), max 64 chars.
    """
    # 1. Lowercase & NFKD Normalize (remove accents)
    key = unicodedata.normalize('NFKD', raw_key).encode('ASCII', 'ignore').decode('utf-8').lower()
    
    # 2. Replace whitespace with underscores
    key = re.sub(r"\s+", "_", key)
    
    # 3. Remove non-alphanumeric (except _, ., :, /, -)
    key = re.sub(r"[^a-z0-9_./:\-]", "", key)
    
    # 4. Cleanup: 
    # - Remove underscores around slashes: _/_ -> /
    # - Remove leading/trailing underscores/slashes? No, slashes might be valid start?
    #   The regex ^[a-z0-9_]+... implies start must be alphanumeric or underscore.
    #   Let's strip underscores from ends.
    key = key.strip("_")
    
    # - Collapse multiple underscores
    key = re.sub(r"_+", "_", key)
    
    # - Remove underscores adjacent to slash
    key = re.sub(r"_?/_?", "/", key)
    
    # 5. Max length 64 chars
    if len(key) > 64:
        key = key[:64]
        
    return key
