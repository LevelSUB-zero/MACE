import json
import jsonschema
import os

# Load schema bundle
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "../../../schemas/ra9_schema_bundle.json")
_SCHEMA_BUNDLE = None

def _get_schema_bundle():
    global _SCHEMA_BUNDLE
    if _SCHEMA_BUNDLE is None:
        with open(SCHEMA_PATH, "r") as f:
            _SCHEMA_BUNDLE = json.load(f)
    return _SCHEMA_BUNDLE

class ActionRequest:
    def __init__(self, request_id, action_type, payload, status="pending"):
        self.request_id = request_id
        self.action_type = action_type
        self.payload = payload
        self.status = status
        self.evidence = []
        
    def to_dict(self):
        return {
            "request_id": self.request_id,
            "action_type": self.action_type,
            "payload": self.payload,
            "status": self.status,
            "evidence": self.evidence
        }
        
    def validate(self):
        """
        Validate against schema.
        """
        bundle = _get_schema_bundle()
        resolver = jsonschema.RefResolver.from_schema(bundle)
        schema = bundle["definitions"]["ActionRequest"]
        jsonschema.validate(self.to_dict(), schema, resolver=resolver)
        return True
