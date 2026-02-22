"""
Training Data Schema and Generation Utilities

Format: JSONL with fields:
- text: Input text
- intent: Intent class
- memory_target: Memory routing target (derived from INTENT_TO_MEMORY or explicit)
- entities: Optional extracted entities
- confidence_hint: Optional difficulty indicator (1.0=easy, 0.5=hard negative)
"""
import json
import os
from typing import List, Dict, Optional
from .config import INTENT_CLASSES, INTENT_TO_MEMORY, DATA_DIR


def create_example(
    text: str,
    intent: str,
    memory_target: Optional[str] = None,
    entities: Optional[Dict] = None,
    confidence_hint: float = 1.0
) -> Dict:
    """
    Create a training example.
    
    Args:
        text: Input text
        intent: Intent class (must be in INTENT_CLASSES)
        memory_target: Memory target (auto-derived if None)
        entities: Optional dict of extracted entities
        confidence_hint: 1.0=clear example, 0.5=hard negative
    
    Returns:
        Training example dict
    """
    if intent not in INTENT_CLASSES:
        raise ValueError(f"Unknown intent: {intent}. Must be one of {INTENT_CLASSES}")
    
    if memory_target is None:
        memory_target = INTENT_TO_MEMORY.get(intent, "none")
    
    return {
        "text": text.strip(),
        "intent": intent,
        "memory_target": memory_target,
        "entities": entities or {},
        "confidence_hint": confidence_hint
    }


def save_examples(examples: List[Dict], filepath: str):
    """Save examples to JSONL file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    print(f"Saved {len(examples)} examples to {filepath}")


def load_examples(filepath: str) -> List[Dict]:
    """Load examples from JSONL file."""
    examples = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))
    return examples


def validate_examples(examples: List[Dict]) -> tuple:
    """
    Validate training examples.
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    for i, ex in enumerate(examples):
        if "text" not in ex:
            errors.append(f"Example {i}: missing 'text'")
        if "intent" not in ex:
            errors.append(f"Example {i}: missing 'intent'")
        elif ex["intent"] not in INTENT_CLASSES:
            errors.append(f"Example {i}: unknown intent '{ex['intent']}'")
    
    return len(errors) == 0, errors


def get_class_distribution(examples: List[Dict]) -> Dict[str, int]:
    """Get count of examples per intent class."""
    dist = {c: 0 for c in INTENT_CLASSES}
    for ex in examples:
        intent = ex.get("intent", "unknown")
        if intent in dist:
            dist[intent] += 1
    return dist


def check_balance(examples: List[Dict], min_per_class: int = 50) -> Dict:
    """
    Check if training data is balanced.
    
    Returns:
        Dict with balance info and recommendations
    """
    dist = get_class_distribution(examples)
    
    # Separate memory actions vs rejections
    memory_action_count = sum(
        dist[i] for i in INTENT_CLASSES if INTENT_TO_MEMORY.get(i, "none") != "none"
    )
    rejection_count = sum(
        dist[i] for i in INTENT_CLASSES if INTENT_TO_MEMORY.get(i, "none") == "none"
    )
    
    underrepresented = [c for c, count in dist.items() if count < min_per_class and count > 0]
    missing = [c for c, count in dist.items() if count == 0]
    
    return {
        "total": len(examples),
        "memory_actions": memory_action_count,
        "rejections": rejection_count,
        "balance_ratio": f"{memory_action_count}:{rejection_count}",
        "underrepresented": underrepresented,
        "missing_classes": missing,
        "per_class": dist
    }
