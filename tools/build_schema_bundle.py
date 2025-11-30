import json
import os
import glob

# Load original bundle to keep skeleton
with open("schemas/ra9_json_schemas.json", "r") as f:
    content = f.read()
    import re
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # content = re.sub(r'//.*', '', content)
    bundle = json.loads(content)

# Clear definitions to rebuild them
bundle["definitions"] = {}

# Load all definitions from directory
def_files = glob.glob("schemas/definitions/*.json")
for file_path in def_files:
    name = os.path.splitext(os.path.basename(file_path))[0]
    with open(file_path, "r") as f:
        schema = json.load(f)
    bundle["definitions"][name] = schema
    print(f"Loaded {name}")

# Write back to bundle
with open("schemas/ra9_json_schemas.json", "w") as f:
    json.dump(bundle, f, indent=2)

print("Rebuilt schemas/ra9_json_schemas.json")
