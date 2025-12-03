import json
import sys
import jsonschema
import os

def validate(schema_path, instance_path):
    print(f"Validating {instance_path} against {schema_path}...")
    
    with open(schema_path, 'r') as f:
        bundle = json.load(f)
        
    # Create a resolver for the bundle
    resolver = jsonschema.RefResolver.from_schema(bundle)
    
    # Load instance
    with open(instance_path, 'r') as f:
        # Handle jsonl
        if instance_path.endswith('.jsonl'):
            lines = f.readlines()
            instances = [json.loads(line) for line in lines]
        else:
            instances = [json.load(f)]
            
    # Determine which schema to use based on filename or content?
    # For now, let's try to infer or pass it as arg.
    # But the tool signature in plan was `tools/jsonschema_validate schemas/ra9_schema_bundle.json samples/reflective_sample.json`
    # We need to know WHICH definition to validate against.
    
    filename = os.path.basename(instance_path)
    schema_name = None
    
    if "reflective" in filename:
        schema_name = "ReflectiveLogEntry"
    elif "sem_snapshot" in filename:
        schema_name = "SemSnapshot"
    elif "selfrep" in filename:
        schema_name = "SelfRepresentationSnapshot"
    elif "brainstate" in filename:
        schema_name = "BrainStateSnapshot"
        
    if not schema_name and "selfrep" in filename:
         # Quick fix: validate it as an object with nodes/edges
         # Or I should have added SelfRepresentationSnapshot to the schema.
         # Let's skip strict schema name check for now and just check if I can find a matching definition?
         # No, I'll update the schema bundle if needed.
         pass

    if schema_name:
        definition = bundle["definitions"][schema_name]
        for instance in instances:
            jsonschema.validate(instance, definition, resolver=resolver)
        print(f"PASS: {instance_path}")
    else:
        print(f"WARN: No matching schema definition found for {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python jsonschema_validate.py <schema_bundle> <instance_file>")
        sys.exit(1)
        
    validate(sys.argv[1], sys.argv[2])
