"""
Schema Validator for MemoryAction

Validates NLU training data against the hardened MemoryAction.json schema.
"""
import json
import os
from typing import List, Dict, Tuple

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    raise ImportError("jsonschema not installed. Run: pip install jsonschema")


# Paths
SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", 
    "schemas", "definitions", "MemoryAction.json"
)
DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..",
    "data", "nlu", "training_data.jsonl"
)


def load_schema() -> Dict:
    """Load the MemoryAction schema."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_example(example: Dict, schema: Dict) -> Tuple[bool, str]:
    """
    Validate a single example against the schema.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        validate(instance=example, schema=schema)
        return True, ""
    except ValidationError as e:
        return False, f"{e.message} at {list(e.absolute_path)}"


def validate_training_data(filepath: str = None) -> Dict:
    """
    Validate all training data against the schema.
    
    Returns:
        {
            "total": int,
            "valid": int,
            "invalid": int,
            "errors": [(line_num, text, error), ...]
        }
    """
    if filepath is None:
        filepath = DATA_PATH
    
    schema = load_schema()
    
    results = {
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "errors": []
    }
    
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            results["total"] += 1
            
            try:
                example = json.loads(line)
            except json.JSONDecodeError as e:
                results["invalid"] += 1
                results["errors"].append((line_num, line[:50], f"JSON parse error: {e}"))
                continue
            
            is_valid, error = validate_example(example, schema)
            
            if is_valid:
                results["valid"] += 1
            else:
                results["invalid"] += 1
                text = example.get("text", "")[:40]
                results["errors"].append((line_num, text, error))
    
    return results


def print_validation_report(results: Dict):
    """Print validation report."""
    print("=" * 60)
    print("SCHEMA VALIDATION REPORT")
    print("=" * 60)
    
    print(f"\nTotal examples: {results['total']}")
    print(f"Valid: {results['valid']} ({100*results['valid']/max(1,results['total']):.1f}%)")
    print(f"Invalid: {results['invalid']}")
    
    if results["errors"]:
        print(f"\nErrors ({len(results['errors'])}):")
        for line_num, text, error in results["errors"][:10]:  # Show first 10
            print(f"  Line {line_num}: '{text}...'")
            print(f"    → {error}")
        
        if len(results["errors"]) > 10:
            print(f"  ... and {len(results['errors']) - 10} more errors")
    else:
        print("\n✓ All examples valid!")


if __name__ == "__main__":
    results = validate_training_data()
    print_validation_report(results)
