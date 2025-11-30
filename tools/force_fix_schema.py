import os

file_path = "schemas/ra9_json_schemas.json"

correct_evidence_object = """    "EvidenceObject": {
      "type": "object",
      "required": [
        "evidence_id",
        "type",
        "content",
        "source",
        "created_at",
        "provenance"
      ],
      "properties": {
        "evidence_id": {
          "type": "string"
        },
        "type": {
          "type": "string"
        },
        "content": {
          "type": "object",
          "properties": {
            "text": {
              "type": "string"
            },
            "structured": {
              "type": [
                "object",
                "null"
              ]
            }
          }
        },
        "source": {
          "type": "object",
          "properties": {
            "origin": {
              "type": "string"
            },
            "reference": {
              "type": "string"
            },
            "fetch_seed": {
              "type": [
                "string",
                "integer"
              ]
            }
          }
        },
        "verifier": {
          "type": [
            "object",
            "null"
          ],
          "properties": {
            "verified_by": {
              "type": "string"
            },
            "verified_at": {
              "type": "string",
              "format": "date-time"
            },
            "verification_method": {
              "type": "string"
            },
            "verification_confidence": {
              "type": "number"
            }
          }
        },
        "summary": {
          "type": "string"
        },
        "confidence": {
          "type": "number"
        },
        "created_at": {
          "type": "string",
          "format": "date-time"
        },
        "provenance": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "step": {
                "type": "string"
              },
              "actor": {
                "type": "string"
              },
              "timestamp": {
                "type": "string",
                "format": "date-time"
              },
              "note": {
                "type": "string"
              }
            }
          }
        },
        "raw_payload": {
          "type": [
            "string",
            "null"
          ]
        }
      },
      "additionalProperties": false
    },
"""

with open(file_path, "r") as f:
    lines = f.readlines()

# Find start of EvidenceObject
start_idx = -1
for i, line in enumerate(lines):
    if '"EvidenceObject": {' in line:
        start_idx = i
        break

# Find start of ExtendedRouterDecision comment block
end_idx = -1
for i, line in enumerate(lines):
    if '10. ROUTER DECISION' in line:
        # The comment block starts 1 line before this usually
        end_idx = i - 1
        break

if start_idx != -1 and end_idx != -1:
    print(f"Replacing lines {start_idx} to {end_idx}")
    # Check if end_idx is correct (it should be the line with /*)
    if "/*" not in lines[end_idx]:
        print(f"Warning: Line {end_idx} does not look like comment start: {lines[end_idx]}")
        # Try to find the /* line
        if "/*" in lines[end_idx-1]:
            end_idx = end_idx - 1
    
    new_lines = lines[:start_idx] + [correct_evidence_object] + lines[end_idx:]
    
    with open(file_path, "w") as f:
        f.writelines(new_lines)
    print("Fixed EvidenceObject schema!")
else:
    print(f"Could not find indices: start={start_idx}, end={end_idx}")
