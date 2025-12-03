import json
import os

# Load existing schema
with open("schemas/ra9_json_schemas.json", "r") as f:
    schema = json.load(f)

# New definitions
new_definitions = {
    "SelfRepresentationNode": {
      "type": "object",
      "required": ["module_id", "version", "capabilities", "status"],
      "properties": {
        "module_id": { "type": "string" },
        "version": { "type": "string" },
        "capabilities": { "type": "array", "items": { "type": "string" } },
        "status": { "type": "string", "enum": ["active", "draining", "offline"] },
        "config": { "type": "object" }
      },
      "additionalProperties": False
    },
    "SelfRepresentationEdge": {
      "type": "object",
      "required": ["from", "to", "type", "weight"],
      "properties": {
        "from": { "type": "string" },
        "to": { "type": "string" },
        "type": { "type": "string" },
        "weight": { "type": "number" }
      },
      "additionalProperties": False
    },
    "BrainStateSnapshot": {
      "type": "object",
       "required": ["snapshot_id", "goals", "working_memory"],
       "properties": {
         "snapshot_id": { "type": "string" },
         "goals": { "type": "array", "items": { "type": "string" } },
         "working_memory": { "type": "array", "items": { "$ref": "#/definitions/MemoryItem" } },
         "attention_gain": { "type": "number" },
         "explore_bias": { "type": "number" }
       },
       "additionalProperties": False
    },
    "APTEvent": {
      "type": "object",
      "required": ["event_id", "node_id", "type", "payload", "sequence_idx"],
      "properties": {
        "event_id": { "type": "string" },
        "node_id": { "type": "string" },
        "type": { "type": "string" },
        "payload": { "type": "object" },
        "sequence_idx": { "type": "integer" },
        "timestamp": { "type": "string", "format": "date-time" }
      },
      "additionalProperties": False
    },
    "ActionRequest": {
        "type": "object",
        "required": ["request_id", "action_type", "payload", "status"],
        "properties": {
            "request_id": { "type": "string" },
            "action_type": { "type": "string" },
            "payload": { "type": "object" },
            "status": { "type": "string", "enum": ["pending", "approved", "rejected", "executed"] },
            "evidence": { "type": "array", "items": { "type": "string" } }
        },
        "additionalProperties": False
    },
    "EpisodicEntry": {
        "type": "object",
        "required": ["episodic_id", "summary", "payload"],
        "properties": {
            "episodic_id": { "type": "string" },
            "summary": { "type": "string" },
            "payload": { "type": "object" },
            "provenance": { "type": "object" }
        },
        "additionalProperties": False
    },
    "SemSnapshot": {
        "type": "object",
        "required": ["snapshot_id", "items"],
        "properties": {
            "snapshot_id": { "type": "string" },
            "items": { "type": "object" }
        },
        "additionalProperties": False
    },
    "SelfRepresentationSnapshot": {
        "type": "object",
        "required": ["nodes", "edges"],
        "properties": {
            "nodes": { 
                "type": "array", 
                "items": { "$ref": "#/definitions/SelfRepresentationNode" } 
            },
            "edges": { 
                "type": "array", 
                "items": { "$ref": "#/definitions/SelfRepresentationEdge" } 
            }
        },
        "additionalProperties": False
    }
}

# Update definitions
schema["definitions"].update(new_definitions)

# Update ReflectiveLogEntry
rle = schema["definitions"]["ReflectiveLogEntry"]
rle["properties"]["immutable_subpayload"] = { "type": "object" }
rle["properties"]["signature"] = { "type": "string" }
rle["properties"]["signature_key_id"] = { "type": "string" }
rle["required"].extend(["immutable_subpayload", "signature", "signature_key_id"])

# Add to top-level schemas
schema["properties"]["schemas"]["properties"].update({
    "SelfRepresentationNode": { "$ref": "#/definitions/SelfRepresentationNode" },
    "SelfRepresentationEdge": { "$ref": "#/definitions/SelfRepresentationEdge" },
    "BrainStateSnapshot": { "$ref": "#/definitions/BrainStateSnapshot" },
    "APTEvent": { "$ref": "#/definitions/APTEvent" },
    "ActionRequest": { "$ref": "#/definitions/ActionRequest" },
    "EpisodicEntry": { "$ref": "#/definitions/EpisodicEntry" },
    "SemSnapshot": { "$ref": "#/definitions/SemSnapshot" }
})

# Save
with open("schemas/ra9_schema_bundle.json", "w") as f:
    json.dump(schema, f, indent=2)

print("Generated schemas/ra9_schema_bundle.json")
