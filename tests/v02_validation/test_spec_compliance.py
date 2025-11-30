import unittest
import json
import os
import jsonschema
from datetime import datetime, timezone

class TestSpecCompliance(unittest.TestCase):
    def setUp(self):
        # Load schema, stripping comments
        with open("schemas/ra9_json_schemas.json", "r") as f:
            content = f.read()
            # Strip C-style comments
            import re
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            # content = re.sub(r'//.*', '', content) # Removed as it breaks URLs
            print(f"DEBUG: First 100 chars: {repr(content[:100])}")
            try:
                self.full_schema = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON Error: {e}")
                print(f"DEBUG: Error context: {repr(content[e.pos-20:e.pos+20])}")
                raise
        self.log_schema = self.full_schema["definitions"]["ReflectiveLogEntry"]
        
        # Resolve refs manually for validation if needed, or rely on resolver
        # For simplicity, we'll use a resolver if possible, or just validate against the full bundle with a ref
        
    def test_v002_log_structure(self):
        """
        Validate a manually constructed v0.0.2 ReflectiveLogEntry against the schema.
        Key requirements:
        - evidence_items is array of EvidenceObject
        - EvidenceObject has verifier: null (allowed)
        - AgentOutput reasoning_trace is string
        """
        
        # Construct sample v0.0.2 log
        sample_log = {
            "log_id": "log_deterministic_123",
            "timestamp": "2025-11-29T12:00:00Z",
            "percept": {
                "percept_id": "percept_123",
                "text": "What is my favorite color?",
                "intent": "profile_lookup",
                "complexity": 1,
                "urgency": "low",
                "risk": "none",
                "timestamp": "2025-11-29T12:00:00Z"
            },
            "router_decision": {
                "decision_id": "dec_123",
                "percept_id": "percept_123",
                "selected_agents": [
                    {"agent_id": "profile_agent", "role": "primary", "budget_tokens": 100}
                ],
                "qcp_snapshot": {},
                "router_features_used": ["regex_match_R2"],
                "depth_level": 1,
                "memory_strategy": "sem_only",
                "memory_routing_decision": {},
                "budget": {
                    "token_budget": 0,
                    "time_budget_ms": 0,
                    "cost_estimate": 0.0
                },
                "brainstate_snapshot": {},
                "fallback_policy": "generic_agent",
                "explain": "matched_R2_profile",
                "created_at": "2025-11-29T12:00:00Z",
                "created_by": "router_stage0",
                "random_seed": 12345
            },
            "council_votes": [
                {
                    "vote_id": "vote_1",
                    "agent_id": "profile_agent",
                    "correctness": 1.0,
                    "relevance": 1.0,
                    "safety": 1.0,
                    "coherence": 1.0,
                    "approve": True,
                    "explain": "stage0_stub"
                }
            ],
            "claims": [],
            "evidence_items": [
                {
                    "evidence_id": "ev_1",
                    "type": "sem_read_snapshot",
                    "content": {
                        "text": "blue",
                        "structured": {"value": "blue"}
                    },
                    "source": {
                        "origin": "sem",
                        "reference": "user/profile/user_tuff/favorite_color",
                        "fetch_seed": 12345
                    },
                    "verifier": None, # Allowed in v0.0.2
                    "summary": "snapshot",
                    "confidence": 1.0,
                    "created_at": "2025-11-29T12:00:00Z",
                    "provenance": [],
                    "raw_payload": "blue"
                }
            ],
            "memory_reads": ["user/profile/user_tuff/favorite_color"],
            "memory_writes": [],
            "brainstate_before": {},
            "brainstate_after": {},
            "final_output": {
                "text": "Your favorite color is blue.",
                "confidence": 1.0,
                "speculative": False
            },
            "random_seed": 12345,
            "model_versions": ["mace-0.1.0"],
            "errors": []
        }
        
        # Validate
        # We need to validate against the full schema bundle to resolve refs
        # But the root is "properties": {"schemas": ...}
        # So we can validate sample_log against "#/definitions/ReflectiveLogEntry"
        
        resolver = jsonschema.RefResolver.from_schema(self.full_schema)
        jsonschema.validate(instance=sample_log, schema=self.log_schema, resolver=resolver)
        print("Validation successful!")

if __name__ == "__main__":
    unittest.main()
