"""
Convert MACE NLU training data (JSON) to BIO format for DistilBERT.

Input:  data/nlu/generated_training_data.jsonl (JSON with entities)
Output: data/nlu/bio_training_data.jsonl (BIO-tagged for token classification)
"""
import json
import os
import re
from typing import List, Tuple, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
INPUT_FILE = os.path.join(BASE_DIR, "data", "nlu", "generated_training_data.jsonl")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "nlu", "bio_training_data.jsonl")


def tokenize_simple(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer that preserves alignment."""
    # Split on whitespace, keeping punctuation attached
    tokens = text.split()
    return tokens


def find_entity_spans(text: str, tokens: List[str], entities: Dict) -> List[str]:
    """
    Align entity values to tokens using substring matching.
    Returns BIO tags for each token.
    
    Example:
        text: "My name is Bob Smith"
        tokens: ["My", "name", "is", "Bob", "Smith"]
        entities: {"name": "Bob Smith"}
        → ["O", "O", "O", "B-name", "I-name"]
    """
    tags = ["O"] * len(tokens)
    
    if not entities:
        return tags
    
    # Build token positions in lowercase text
    text_lower = text.lower()
    token_positions = []
    pos = 0
    for tok in tokens:
        # Find this token in the text starting from current pos
        idx = text_lower.find(tok.lower(), pos)
        if idx == -1:
            idx = pos  # fallback
        token_positions.append((idx, idx + len(tok)))
        pos = idx + len(tok)
    
    # For each entity, find which tokens it spans
    for entity_key, entity_value in entities.items():
        if not isinstance(entity_value, str):
            entity_value = str(entity_value)
        
        val_lower = entity_value.lower()
        
        # Find the entity value in the text
        start_idx = text_lower.find(val_lower)
        if start_idx == -1:
            # Try fuzzy: entity might not be exact substring
            continue
        
        end_idx = start_idx + len(val_lower)
        
        # Find which tokens overlap with this span
        entity_tokens = []
        for i, (tok_start, tok_end) in enumerate(token_positions):
            if tok_start >= start_idx and tok_end <= end_idx:
                entity_tokens.append(i)
            elif tok_start < end_idx and tok_end > start_idx:
                entity_tokens.append(i)
        
        # Apply BIO tags
        for j, tok_idx in enumerate(entity_tokens):
            if tags[tok_idx] == "O":  # Don't overwrite existing tags
                if j == 0:
                    tags[tok_idx] = f"B-{entity_key}"
                else:
                    tags[tok_idx] = f"I-{entity_key}"
    
    return tags


def convert_example(example: Dict) -> Dict:
    """Convert a single training example to BIO format."""
    text = example.get("text", "")
    intent = example.get("root_intent", "unknown")
    memory_type = example.get("memory_type", "none")
    complexity = example.get("complexity", "atomic")
    entities = example.get("entities", {})
    
    tokens = tokenize_simple(text)
    bio_tags = find_entity_spans(text, tokens, entities)
    
    return {
        "tokens": tokens,
        "bio_tags": bio_tags,
        "intent": intent,
        "memory_type": memory_type,
        "complexity": complexity,
        "text": text,
    }


def collect_labels(data: List[Dict]) -> Dict:
    """Collect all unique labels from the dataset."""
    intents = sorted(set(d["intent"] for d in data))
    memory_types = sorted(set(d["memory_type"] for d in data))
    complexity_types = sorted(set(d["complexity"] for d in data))
    
    # Collect all unique BIO tags
    bio_tags = set(["O"])
    for d in data:
        for tag in d["bio_tags"]:
            bio_tags.add(tag)
    bio_tags = sorted(bio_tags)
    
    return {
        "intents": intents,
        "memory_types": memory_types,
        "complexity_types": complexity_types,
        "bio_tags": bio_tags,
        "intent2id": {v: i for i, v in enumerate(intents)},
        "id2intent": {i: v for i, v in enumerate(intents)},
        "memory2id": {v: i for i, v in enumerate(memory_types)},
        "id2memory": {i: v for i, v in enumerate(memory_types)},
        "bio2id": {v: i for i, v in enumerate(bio_tags)},
        "id2bio": {i: v for i, v in enumerate(bio_tags)},
    }


def main():
    """Convert JSON training data to BIO format."""
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Not found: {INPUT_FILE}")
        return
    
    # Load examples
    examples = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    print(f"📊 Loaded {len(examples)} examples")
    
    # Convert to BIO
    bio_data = [convert_example(ex) for ex in examples]
    
    # Collect label sets
    labels = collect_labels(bio_data)
    
    print(f"📋 Intents: {len(labels['intents'])}")
    print(f"📋 Memory types: {len(labels['memory_types'])}")
    print(f"📋 BIO tags: {len(labels['bio_tags'])}")
    
    # Save BIO data
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for item in bio_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    # Save label maps
    label_file = os.path.join(os.path.dirname(OUTPUT_FILE), "label_maps.json")
    with open(label_file, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved {len(bio_data)} BIO examples → {OUTPUT_FILE}")
    print(f"✅ Saved label maps → {label_file}")
    
    # Show samples
    print("\n--- Samples ---")
    for ex in bio_data[:3]:
        print(f"\n  Text: {ex['text']}")
        print(f"  Intent: {ex['intent']}")
        aligned = list(zip(ex['tokens'], ex['bio_tags']))
        non_o = [(t, tag) for t, tag in aligned if tag != "O"]
        if non_o:
            print(f"  Entities: {non_o}")
        else:
            print(f"  Entities: (none)")
    
    # Stats
    entity_count = sum(1 for d in bio_data if any(t != "O" for t in d["bio_tags"]))
    print(f"\n📊 Examples with entities: {entity_count}/{len(bio_data)}")
    print(f"📊 BIO tags: {labels['bio_tags'][:20]}...")


if __name__ == "__main__":
    main()
