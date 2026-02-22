"""
MACE NLU Data Standardizer
Converts diverse training data into a Single Strict Schema for Behavior Shaping.

Input: data/nlu/generated_training_data.jsonl
Output: data/nlu/standardized_training_data.jsonl

Schema:
- text
- root_intent
- memory_type
- complexity
- entities: {
    task, time, person, location, topic, attribute, value, target
  } (all nullable)
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
INPUT_FILE = os.path.join(BASE_DIR, "data", "nlu", "generated_training_data.jsonl")
OUTPUT_FILE = INPUT_FILE  # Overwrite with standardized data

# ==========================================
# MAPPINGS
# ==========================================
KEY_MAPPING = {
    # Person
    "contact_name": "person",
    "name": "person",
    "recipient": "person",
    "sender": "person",
    "who": "person",
    
    # Time
    "date": "time",
    "datetime": "time",
    "day": "time",
    "deadline": "time",
    "duration": "time",
    "frequency": "time",
    "start_time": "time",
    "end_time": "time",
    "when": "time",
    
    # Location
    "address": "location",
    "city": "location",
    "country": "location",
    "destination": "location",
    "origin": "location",
    "place": "location",
    "spot": "location",
    "where": "location",
    
    # Task/Action
    "action": "task",
    "activity": "task",
    "command": "task",
    "operation": "task",
    "process": "task",
    
    # Topic
    "context": "topic",
    "keywords": "topic",
    "query": "topic",
    "subject": "topic",
    "theme": "topic",
    
    # Value (Generic)
    "amount": "value",
    "count": "value",
    "distance": "value",
    "number": "value",
    "percentage": "value",
    "price": "value",
    "quantity": "value",
    "rating": "value",
    "score": "value",
    "result": "value",
    
    # Attributes (often become attribute+value)
    # Handled dynamically below
}

CORE_SLOTS = ["task", "time", "person", "location", "topic", "attribute", "value", "target"]

def standardize_entities(original_entities):
    """
    Maps varied entity keys to the 8 Core Slots.
    Returns a dict with exactly 8 keys, values are string or None.
    """
    standard = {k: None for k in CORE_SLOTS}
    
    # If using 'structure' (conditional/update), flatten it
    # We treat structure fields as entities for the parser
    # This is a simplification but works for "Behavior Shaping"
    
    for k, v in original_entities.items():
        if v is None: continue
        v_str = str(v)
        
        # 1. Direct Mapping
        if k in CORE_SLOTS:
            standard[k] = v_str
            continue
            
        # 2. Known Aliases
        if k in KEY_MAPPING:
            target_key = KEY_MAPPING[k]
            standard[target_key] = v_str
            continue
            
        # 3. Attribute-Value Pairs (e.g. 'favorite_color': 'blue')
        # Map key to 'attribute', value to 'value'
        # Only if we don't already have an attribute/value pair
        if standard["attribute"] is None and standard["value"] is None:
            standard["attribute"] = k
            standard["value"] = v_str
            continue
            
        # 4. Fallback: Map to 'target' or 'topic'
        if standard["target"] is None:
            standard["target"] = v_str
        elif standard["topic"] is None:
            standard["topic"] = v_str
        else:
            # If all overflow slots taken, append to 'value'
            standard["value"] = (standard["value"] or "") + f", {v_str}"

    return standard

def main():
    print(f"Reading from {INPUT_FILE}...")
    
    data = []
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data.append(json.loads(line))
                    except:
                        pass
    
    print(f"Converting {len(data)} examples...")
    
    standardized = []
    for item in data:
        # Flatten structure if present
        entities = item.get("entities", {})
        if "structure" in item:
            # Flatten structure into entities for parser training
            struct = item["structure"]
            if isinstance(struct, dict):
                entities.update(struct)
        
        if "steps" in item:
            # Flatten steps into a single task string
            steps = item["steps"]
            if isinstance(steps, list):
                combined_tasks = []
                for step in steps:
                    if "entities" in step and "task" in step["entities"]:
                        combined_tasks.append(step["entities"]["task"])
                    elif "intent" in step:
                        combined_tasks.append(step["intent"])
                if combined_tasks:
                    entities["task"] = ", ".join(combined_tasks)
        
        std_entities = standardize_entities(entities)
        
        new_item = {
            "text": item["text"],
            "root_intent": item["root_intent"],
            "memory_type": item["memory_type"],
            "complexity": item["complexity"],
            "entities": std_entities
        }
        standardized.append(new_item)
    
    print(f"Writing {len(standardized)} examples to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for item in standardized:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print("✅ Standardization Complete.")
    print("Sample output:")
    print(json.dumps(standardized[0], indent=2))

if __name__ == "__main__":
    main()
