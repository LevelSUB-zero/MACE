import json
import os

# Ensure directory exists
os.makedirs("schemas/definitions", exist_ok=True)

# Load current bundle
with open("schemas/ra9_json_schemas.json", "r") as f:
    # Strip comments if any (simple regex)
    content = f.read()
    import re
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # content = re.sub(r'//.*', '', content) # Removed to avoid breaking URLs
    bundle = json.loads(content)

definitions = bundle.get("definitions", {})

for name, schema in definitions.items():
    # Apply fix to EvidenceObject if needed
    if name == "EvidenceObject":
        if "verifier" in schema["properties"]:
            print(f"Applying fix to {name}...")
            schema["properties"]["verifier"]["type"] = ["object", "null"]
    
    file_path = f"schemas/definitions/{name}.json"
    with open(file_path, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"Wrote {file_path}")

print("Split complete.")
