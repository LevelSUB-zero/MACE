"""
Convert MACE NLU training data to instruction-tuning format.

Converts generated_training_data.jsonl → instruction_data.jsonl
for fine-tuning LLMs with Unsloth/HuggingFace.
"""
import json
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
INPUT_FILE = os.path.join(BASE_DIR, "data", "nlu", "generated_training_data.jsonl")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "nlu", "instruction_data.jsonl")

# System prompt for the fine-tuned model
SYSTEM_PROMPT = """You are MACE-NLU, a Natural Language Understanding parser for the MACE memory system.
Parse the user's input into a structured MemoryAction JSON object.

Output format:
- text: The original user input
- root_intent: The primary intent (e.g., profile_store, reminder_set, chitchat)
- memory_type: Target memory (wm, cwm, sem, epi, mixed, none)
- complexity: Structure type (atomic, conditional, compound, update, meta, reference_heavy)
- entities: Key-value pairs of extracted information (for atomic)
- structure: Nested structure (for conditional, update, meta, reference_heavy)
- steps: Array of sequential steps (for compound)

Respond ONLY with valid JSON, no explanations."""

def convert_example(example: dict) -> dict:
    """Convert a single example to instruction format."""
    # The input is the user's text
    user_input = example.get("text", "")
    
    # The output is the full structured JSON
    output_json = json.dumps(example, ensure_ascii=False)
    
    return {
        "instruction": "Parse this user input into a MemoryAction JSON structure.",
        "input": user_input,
        "output": output_json,
        "system": SYSTEM_PROMPT
    }

def convert_to_alpaca_format(example: dict) -> dict:
    """Convert to Alpaca-style format (alternative)."""
    user_input = example.get("text", "")
    output_json = json.dumps(example, ensure_ascii=False)
    
    return {
        "instruction": f"{SYSTEM_PROMPT}\n\nParse this input:",
        "input": user_input,
        "output": output_json
    }

def convert_to_chatml_format(example: dict) -> dict:
    """Convert to ChatML format for chat-based models."""
    user_input = example.get("text", "")
    output_json = json.dumps(example, ensure_ascii=False)
    
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse: {user_input}"},
            {"role": "assistant", "content": output_json}
        ]
    }

def main(format_type="chatml"):
    """
    Convert training data to instruction format.
    
    Args:
        format_type: "standard", "alpaca", or "chatml"
    """
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found!")
        return
    
    examples = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    print(f"Loaded {len(examples)} examples from {INPUT_FILE}")
    
    # Convert based on format
    converted = []
    for ex in examples:
        if format_type == "alpaca":
            converted.append(convert_to_alpaca_format(ex))
        elif format_type == "chatml":
            converted.append(convert_to_chatml_format(ex))
        else:
            converted.append(convert_example(ex))
    
    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for item in converted:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"Saved {len(converted)} examples to {OUTPUT_FILE}")
    print(f"Format: {format_type}")
    
    # Show sample
    print("\n--- Sample Output ---")
    print(json.dumps(converted[0], indent=2, ensure_ascii=False)[:500] + "...")

if __name__ == "__main__":
    import sys
    fmt = sys.argv[1] if len(sys.argv) > 1 else "chatml"
    main(format_type=fmt)
