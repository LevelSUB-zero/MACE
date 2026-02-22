"""
MACE NLU Data Generator (Targeted Templates)
Generates 500+ diverse training examples for specific weak intents using templates.
No LLM required. Fast & Deterministic.
"""
import json
import random
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "nlu", "generated_training_data.jsonl")

# ==========================================
# TEMPLATES
# ==========================================

PERSONAS = {
    "standard": lambda s: s,
    "impatient": lambda s: s.replace("please ", "").replace("could you ", "").replace("I would like to ", "").lower(),
    "formal": lambda s: f"Could you please {s}?" if not s.endswith("?") else f"I inquire: {s}",
    "casual": lambda s: s.lower().replace("going to", "gonna").replace("want to", "wanna").replace("because", "cuz"),
}

TEMPLATES = [
    # === MATH (100 examples) ===
    {
        "intent": "math", "mem": "none", "comp": "atomic",
        "patterns": [
            "calculate {N1} {OP} {N2}",
            "what is {N1} {OP} {N2}",
            "compute {N1} {OP} {N2}",
            "solve {N1} {OP} {N2}",
            "{N1} {OP} {N2}",
            "how much is {N1} {OP} {N2}",
        ],
        "vars": {
            "N1": range(1, 100),
            "N2": range(1, 100),
            "OP": ["plus", "minus", "times", "divided by", "+", "-", "*", "/", "modulo", "power of"]
        }
    },
    
    # === PREFERENCE (100 examples) ===
    {
        "intent": "preference_store", "mem": "sem", "comp": "atomic",
        "patterns": [
            "I like {ITEM}",
            "I hate {ITEM}",
            "my favorite {ATTR} is {VAL}",
            "I prefer {VAL} over {VAL2}",
            "I love {ITEM}",
            "never show me {ITEM}",
            "always choose {ITEM}",
        ],
        "vars": {
            "ITEM": ["pizza", "jazz", "horror movies", "python", "dark mode", "cats", "spicy food", "traveling"],
            "ATTR": ["color", "food", "genre", "language", "theme", "animal", "sport"],
            "VAL": ["blue", "sushi", "rock", "rust", "light", "dogs", "tennis"],
            "VAL2": ["red", "burgers", "pop", "cpp", "dark", "cats", "soccer"]
        }
    },

    # === HISTORY SEARCH (100 examples) ===
    {
        "intent": "history_search", "mem": "epi", "comp": "atomic",
        "patterns": [
            "what did I say about {TOPIC}",
            "when did we discuss {TOPIC}",
            "find the message about {TOPIC}",
            "search related to {TOPIC}",
            "did I mention {TOPIC}",
            "recall the conversation from {TIME}",
        ],
        "vars": {
            "TOPIC": ["the project", "vacation", "budget", "deployment", "error logs", "meeting notes", "Alice"],
            "TIME": ["yesterday", "last week", "Monday", "this morning", "2 days ago"]
        }
    },

    # === AUTOMATION (100 examples) ===
    {
        "intent": "automation_set", "mem": "wm", "comp": "conditional",
        "patterns": [
            "if {TRIGGER} then {ACTION}",
            "whenever {TRIGGER} do {ACTION}",
            "when {TRIGGER} happens execute {ACTION}",
            "set a rule: {TRIGGER} -> {ACTION}",
            "automate this: on {TRIGGER}, {ACTION}",
        ],
        "vars": {
            "TRIGGER": ["I say hello", "email arrives", "time is 8pm", "server crashes", "battery low"],
            "ACTION": ["reply hi", "forward to slack", "turn on lights", "restart service", "notify me"]
        }
    },

    # === FACT CORRECTION (50 examples) ===
    {
        "intent": "fact_correction", "mem": "sem", "comp": "update",
        "patterns": [
            "no, {ATTR} is actually {VAL}",
            "correction: {ATTR} is {VAL}",
            "wrong, I meant {VAL}",
            "change {ATTR} to {VAL}",
            "update my {ATTR} to {VAL}",
        ],
        "vars": {
            "ATTR": ["name", "email", "phone", "address", "birthday"],
            "VAL": ["Alice", "bob@gmail.com", "555-0199", "New York", "June 15th"]
        }
    }
]

def generate():
    data = []
    
    # Generate ~500 examples
    count = 0
    for tmpl in TEMPLATES:
        for _ in range(100):
            pat = random.choice(tmpl["patterns"])
            
            # Fill variables
            text = pat
            entities = {}
            
            # Simple entity extraction heuristic for templates
            # In a real system we'd use cleaner slots, but this works for training
            
            for k, v_list in tmpl["vars"].items():
                val = str(random.choice(list(v_list)))
                if f"{{{k}}}" in text:
                    text = text.replace(f"{{{k}}}", val)
                    # Map template var to standard entity key
                    key_map = {
                        "N1": "value", "N2": "value", "OP": "operator",
                        "ITEM": "value", "ATTR": "attribute", "VAL": "value", "VAL2": "value",
                        "TOPIC": "topic", "TIME": "time",
                        "TRIGGER": "trigger", "ACTION": "action"
                    }
                    std_key = key_map.get(k, k.lower())
                    if std_key in entities:
                        entities[std_key] = entities[std_key] + " " + val
                    else:
                        entities[std_key] = val
            
            # Apply Persona
            persona = random.choice(list(PERSONAS.keys()))
            text = PERSONAS[persona](text)
            
            # Construct Training Item
            item = {
                "text": text,
                "root_intent": tmpl["intent"],
                "memory_type": tmpl["mem"],
                "complexity": tmpl["comp"],
                "entities": entities,
                "_source": f"template_gen_{persona}"
            }
            data.append(item)
            count += 1
            
    print(f"Generated {len(data)} examples.")
    
    # Unique only
    unique_data = {json.dumps(d, sort_keys=True): d for d in data}.values()
    print(f"Unique examples: {len(unique_data)}")

    return list(unique_data)

def main():
    print(f"Generating diverse data using templates...")
    dataset = generate()
    
    print(f"Appending to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for item in dataset:
            clean_item = {k: v for k, v in item.items() if not k.startswith("_")}
            f.write(json.dumps(clean_item) + "\n")
    print("DONE.")

if __name__ == "__main__":
    main()
