import yaml
import os

# Cache for loaded configs
_config_cache = {}

def _load_yaml(filename):
    """Load and cache YAML config file."""
    if filename in _config_cache:
        return _config_cache[filename]
    
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(filepath):
        return {}
    
    with open(filepath, 'r') as f:
        config = yaml.safe_load(f) or {}
    
    _config_cache[filename] = config
    return config

def get_limits():
    """Get limits configuration."""
    return _load_yaml('limits.yaml')

def get_keys():
    """Get keys configuration."""
    return _load_yaml('keys.yaml')

def get_schema_version():
    """Get schema version configuration."""
    return _load_yaml('schema_version.yaml')

# Convenience getters for specific values
def get_wm_capacity():
    """Get working memory capacity limit."""
    return get_limits().get('wm_capacity', 10)

def get_wm_ttl():
    """Get working memory TTL in ticks."""
    return get_limits().get('wm_ttl_ticks', 5)

def get_attention_decay_rate():
    """Get attention decay rate per tick."""
    return get_limits().get('attention_decay', 0.9)

def get_default_token_budget():
    """Get default token budget for agents."""
    return get_limits().get('default_token_budget', 1000)

def get_signing_key(key_id):
    """Get signing key by ID."""
    keys = get_keys()
    return keys.get('signing_keys', {}).get(key_id, 'PLACEHOLDER_KEY_FOR_DEV')

def get_current_schema_version():
    """Get current schema version."""
    return get_schema_version().get('version', '0.0.1')
