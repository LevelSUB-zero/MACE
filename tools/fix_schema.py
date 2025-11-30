import os

file_path = "schemas/ra9_json_schemas.json"

with open(file_path, "r") as f:
    lines = f.readlines()

# Look for the line closing EvidenceObject
# It should be around line 620
# It contains "}," and is followed by a comment block starting with "/*"

for i, line in enumerate(lines):
    if "/*" in lines[i+1] and "ROUTER DECISION" in lines[i+2]:
        # found the spot
        print(f"Found spot at line {i+1}: {line.strip()}")
        if line.strip() == "},":
            print("Comma already exists!")
        elif line.strip() == "}":
            print("Adding comma...")
            lines[i] = line.rstrip() + ",\n"
            with open(file_path, "w") as f:
                f.writelines(lines)
            print("Fixed!")
            break
        else:
            print(f"Unexpected line content: {line}")
