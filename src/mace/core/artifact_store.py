import os
import hashlib

ARTIFACTS_DIR = "artifacts"

def save_artifact(content_bytes):
    """
    Save content to artifacts directory with SHA256 filename.
    Returns: artifact_url (str)
    """
    if not isinstance(content_bytes, bytes):
        if isinstance(content_bytes, str):
            content_bytes = content_bytes.encode('utf-8')
        else:
            raise ValueError("Content must be bytes or string")
        
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    filename = f"{sha256}.bin"
    filepath = os.path.join(ARTIFACTS_DIR, filename)
    
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    with open(filepath, "wb") as f:
        f.write(content_bytes)
        
    return f"artifacts://{filename}"

def get_artifact(artifact_url):
    """
    Retrieve artifact content.
    """
    if not artifact_url.startswith("artifacts://"):
        raise ValueError("Invalid artifact URL scheme")
        
    filename = artifact_url.replace("artifacts://", "")
    # Basic path traversal protection
    if "/" in filename or "\\" in filename or ".." in filename:
         raise ValueError("Invalid artifact filename")
         
    filepath = os.path.join(ARTIFACTS_DIR, filename)
    
    if not os.path.exists(filepath):
        return None
        
    with open(filepath, "rb") as f:
        return f.read()
