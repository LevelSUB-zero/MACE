import unittest
import json
import os
from jsonschema import validate
from mace.runtime import executor
from mace.core import deterministic

SCHEMA_PATH = "schemas/ra9_json_schemas.json"

class TestSchema(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        with open(SCHEMA_PATH, "r") as f:
            content = f.read()
            # Strip comments (/* ... */)
            # Simple regex for C-style comments
            import re
            content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
            cls.schema = json.loads(content)
            
    def setUp(self):
        deterministic.init_seed("schema_test_seed")

    def test_2_1_reflective_log_schema(self):
        """
        2.1 — ReflectiveLog schema validation
        Validate a produced log against JSON schema.
        """
        # Generate log
        res, log_entry = executor.execute("What is 2 + 2?", seed="schema_seed", log_enabled=False)
        
        # Validate
        # The schema has "definitions", and we want to validate against "ReflectiveLogEntry".
        # We can create a wrapper schema that points to ReflectiveLogEntry
        
        # Or we can just use the definitions.
        # jsonschema validate(instance, schema)
        # If we pass the full schema, it validates against the root.
        # The root has "properties": {"schemas": ...}.
        # But log_entry is a ReflectiveLogEntry, not the root bundle.
        
        # We need to extract the definition for ReflectiveLogEntry and resolve refs.
        # A simple way is to use the full schema but specify the ref.
        # But jsonschema doesn't support "validate against this ref" easily without a wrapper.
        
        wrapper_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": self.schema["definitions"],
            "$ref": "#/definitions/ReflectiveLogEntry"
        }
        
        try:
            validate(instance=log_entry, schema=wrapper_schema)
            print("\nPASS: ReflectiveLog schema validation")
        except Exception as e:
            self.fail(f"Schema validation failed: {e}")

    def test_2_2_per_object_validation(self):
        """
        2.2 — Per-object validation (Percept, RouterDecision, AgentOutput, CouncilVote)
        """
        res, log_entry = executor.execute("What is 2 + 2?", seed="obj_seed", log_enabled=False)
        
        # Percept
        percept_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": self.schema["definitions"],
            "$ref": "#/definitions/Percept"
        }
        validate(instance=log_entry["percept"], schema=percept_schema)
        
        # RouterDecision
        router_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": self.schema["definitions"],
            "$ref": "#/definitions/ExtendedRouterDecision"
        }
        validate(instance=log_entry["router_decision"], schema=router_schema)
        
        # CouncilVote (list)
        vote_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": self.schema["definitions"],
            "$ref": "#/definitions/CouncilVote"
        }
        for vote in log_entry["council_votes"]:
            validate(instance=vote, schema=vote_schema)
            
        print("PASS: Per-object schema validation")

if __name__ == "__main__":
    unittest.main()
