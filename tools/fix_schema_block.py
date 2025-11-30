import os

file_path = "schemas/ra9_json_schemas.json"

# Correct content for ClaimExtraction and EvidenceObject
new_block = """    "ClaimExtraction": {
      "type": "object",
      "required": [
        "claim_id",
        "percept_id",
        "text",
        "claim_type",
        "extracted_at",
        "source"
      ],
      "properties": {
        "claim_id": {
          "type": "string"
        },
        "percept_id": {
          "type": "string"
        },
        "text": {
          "type": "string"
        },
        "claim_type": {
          "type": "string"
        },
        "clauses": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "clause_id": {
                "type": "string"
              },
              "text": {
                "type": "string"
              },
              "type": {
                "type": "string"
              },
              "confidence": {
                "type": "number"
              }
            }
          }
        },
        "source": {
          "type": "object",
          "properties": {
            "source_type": {
              "type": "string"
            },
            "source_id": {
              "type": "string"
            },
            "model_version": {
              "type": "string"
            },
            "random_seed": {
              "type": [
                "string",
                "integer"
              ]
            }
          }
        },
        "evidence_refs": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "verification_status": {
          "type": "string"
        },
        "extracted_by": {
          "type": "string"
        },
        "extracted_at": {
          "type": "string",
          "format": "date-time"
        }
      },
      "additionalProperties": false
    },
    /* -------------------------------------------------
       9.  EVIDENCE OBJECT (NEW)
    ---------------------------------------------------*/
    "EvidenceObject": {
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
    /* -------------------------------------------------
       10. ROUTER DECISION (NEW, EXTENDED)
    ---------------------------------------------------*/
"""

with open(file_path, "r") as f:
    lines = f.readlines()

# Find start line (ClaimExtraction)
start_idx = -1
for i, line in enumerate(lines):
    if '"ClaimExtraction": {' in line:
        start_idx = i
        break

# Find end line (ExtendedRouterDecision)
end_idx = -1
for i, line in enumerate(lines):
    if '"ExtendedRouterDecision": {' in line:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    print(f"Replacing lines {start_idx} to {end_idx}")
    
    # We need to preserve the comment block before ExtendedRouterDecision if it's not in new_block
    # But new_block includes the comment block for Router Decision at the end.
    # So we should replace up to ExtendedRouterDecision start.
    
    # Check if end_idx line is the ExtendedRouterDecision line.
    # We want to insert BEFORE it.
    
    # But wait, the comment block for Router Decision is corrupted in the file?
    # In Step 903:
    # 621:                 /* -------------------------------------------------
    # 622:        10. ROUTER DECISION (NEW, EXTENDED)
    # 623:     ---------------------------------------------------*/
    # 624:                 "ExtendedRouterDecision": {
    
    # My new_block ends with the comment block.
    # So I should replace up to ExtendedRouterDecision line.
    
    # However, the indentation of ExtendedRouterDecision in the file is wrong (16 spaces).
    # I should fix it?
    # No, I'll let it be for now, or I can fix it by un-indenting the rest of the file?
    # That's too hard.
    # I'll just replace the block. If ExtendedRouterDecision is indented, it's valid JSON.
    
    # But wait, if I replace the block with correct indentation (4 spaces), and ExtendedRouterDecision is at 16 spaces, it's ugly but valid.
    # The important thing is braces.
    
    # I'll replace lines[start_idx:end_idx] with new_block.
    
    new_lines = lines[:start_idx] + [new_block] + lines[end_idx:]
    
    with open(file_path, "w") as f:
        f.writelines(new_lines)
    print("Fixed schema block!")
else:
    print(f"Could not find start ({start_idx}) or end ({end_idx}) indices.")
