"""
NLU Training Script

Trains the intent + memory classifier on labeled data.

Usage:
    python -m mace.nlu.train
"""
import os
import sys
import json
from typing import List, Dict

# Add src to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from mace.nlu.config import DATA_DIR, TRAINING_DATA_PATH
from mace.nlu.classifier import NLUClassifier
from mace.nlu.training_data import load_examples, validate_examples, check_balance


def load_training_data(filepath: str = None) -> tuple:
    """Load and prepare training data."""
    if filepath is None:
        filepath = TRAINING_DATA_PATH
    
    print(f"Loading training data from {filepath}...")
    examples = load_examples(filepath)
    
    print(f"Loaded {len(examples)} examples")
    
    # Validate
    is_valid, errors = validate_examples(examples)
    if not is_valid:
        print("Validation errors:")
        for e in errors[:10]:
            print(f"  - {e}")
        raise ValueError("Invalid training data")
    
    # Check balance
    balance = check_balance(examples)
    print(f"\nData balance:")
    print(f"  Total: {balance['total']}")
    print(f"  Memory actions: {balance['memory_actions']}")
    print(f"  Rejections: {balance['rejections']}")
    print(f"  Ratio: {balance['balance_ratio']}")
    
    if balance['missing_classes']:
        print(f"  Missing classes: {balance['missing_classes']}")
    
    if balance['underrepresented']:
        print(f"  Underrepresented: {balance['underrepresented']}")
    
    # Extract fields
    texts = [ex["text"] for ex in examples]
    intents = [ex["intent"] for ex in examples]
    memory_targets = [ex["memory_target"] for ex in examples]
    
    return texts, intents, memory_targets


def train(data_path: str = None, save: bool = True) -> Dict:
    """
    Train the NLU classifier.
    
    Args:
        data_path: Path to training data JSONL
        save: Whether to save the trained model
    
    Returns:
        Training metrics
    """
    texts, intents, memory_targets = load_training_data(data_path)
    
    classifier = NLUClassifier()
    metrics = classifier.train(texts, intents, memory_targets, verbose=True)
    
    if save:
        classifier.save()
    
    return metrics


def test_predictions(classifier: NLUClassifier = None):
    """Test predictions on sample inputs."""
    if classifier is None:
        from mace.nlu.classifier import get_classifier
        classifier = get_classifier()
    
    test_cases = [
        "My name is Bob",
        "What is my name?",
        "I hate spicy food",
        "What is 2 + 2?",
        "Hello there!",
        "asdf jkl",
        "I'm starting to cook dinner",
        "What did we discuss yesterday?",
        "The gate code is 1234",
        "Nice weather today",
        "I think I might go somewhere",
    ]
    
    print("\n=== Sample Predictions ===")
    for text in test_cases:
        pred = classifier.predict(text)
        conf_str = "✓" if pred["is_confident"] else "?"
        print(f"{conf_str} '{text[:35]:35}' -> {pred['intent']:18} ({pred['intent_confidence']:.2f}) -> {pred['memory_target']}")


if __name__ == "__main__":
    print("=" * 60)
    print("NLU Model Training")
    print("=" * 60)
    
    metrics = train()
    
    print("\n" + "=" * 60)
    print("Testing Predictions")
    print("=" * 60)
    
    from mace.nlu.classifier import get_classifier
    test_predictions(get_classifier())
