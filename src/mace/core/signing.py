import hmac
import hashlib
import os
import yaml
from mace.core import canonical

# Load keys config
KEYS_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "../config/keys.yaml")
_keys_config = {}

def _load_keys_config():
    global _keys_config
    if not _keys_config and os.path.exists(KEYS_CONFIG_FILE):
        with open(KEYS_CONFIG_FILE, "r") as f:
            _keys_config = yaml.safe_load(f)

def _get_secret_key(key_id):
    """
    Retrieve the secret key for a given key_id.
    In a real environment, this would fetch from Vault.
    For Stage-1 dev/CI, we use env vars or a default test key.
    """
    # Check env var first (e.g. MACE_KEY_vault_mace_signing_key_v1)
    env_var_name = "MACE_KEY_" + key_id.replace(":", "_").replace("-", "_")
    if env_var_name in os.environ:
        return os.environ[env_var_name]
    
    # Fallback for CI/Dev if allowed
    # In strict prod, this should fail.
    # For now, return a deterministic test key based on key_id
    return f"test_secret_for_{key_id}"

def sign_payload(payload, key_id):
    """
    Sign a payload (dict or list) using HMAC-SHA256.
    Returns the hex signature.
    """
    _load_keys_config()
    
    # 1. Canonicalize
    serialized = canonical.canonical_json_serialize(payload)
    
    # 2. Get Key
    secret = _get_secret_key(key_id)
    if isinstance(secret, str):
        secret = secret.encode('utf-8')
        
    # 3. HMAC
    signature = hmac.new(secret, serialized.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def verify_signature(payload, signature, key_id):
    """
    Verify the signature of a payload.
    Returns True if valid, False otherwise.
    """
    expected_signature = sign_payload(payload, key_id)
    return hmac.compare_digest(signature, expected_signature)
