"""
Multi-Head Intent + Memory Classifier

Architecture:
- Shared sentence embedding (from embedder.py)
- Intent classification head (29 classes)
- Memory routing head (5 classes)

Uses sklearn for simplicity and fast inference.
"""
import os
import pickle
import numpy as np
from typing import Dict, Tuple, List, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from .config import (
    ROOT_INTENTS, MEMORY_TYPES, INTENT_TO_MEMORY,
    CONFIDENCE_THRESHOLD, CLASSIFIER_PATH, MODEL_DIR
)
from .embedder import embed

# Aliases for backward compatibility
INTENT_CLASSES = ROOT_INTENTS
MEMORY_CLASSES = MEMORY_TYPES


class NLUClassifier:
    """
    Multi-head classifier for intent and memory routing.
    """
    
    def __init__(self):
        self.intent_encoder = LabelEncoder()
        self.memory_encoder = LabelEncoder()
        
        # Fit encoders with all possible classes
        self.intent_encoder.fit(INTENT_CLASSES)
        self.memory_encoder.fit(MEMORY_CLASSES)
        
        # Classifiers (will be trained)
        self.intent_clf = None
        self.memory_clf = None
        
        self.is_trained = False
    
    def train(
        self,
        texts: List[str],
        intents: List[str],
        memory_targets: List[str],
        test_size: float = 0.2,
        verbose: bool = True
    ) -> Dict:
        """
        Train the classifier on labeled data.
        
        Args:
            texts: List of input texts
            intents: List of intent labels
            memory_targets: List of memory target labels
            test_size: Fraction for validation
            verbose: Print training progress
        
        Returns:
            Training metrics
        """
        if verbose:
            print(f"Training NLU classifier on {len(texts)} examples...")
        
        # Get embeddings
        if verbose:
            print("Generating embeddings...")
        X = embed(texts)
        
        # Encode labels
        y_intent = self.intent_encoder.transform(intents)
        y_memory = self.memory_encoder.transform(memory_targets)
        
        # For small datasets, train on all data without validation
        n_classes = len(set(intents))
        min_examples_for_split = max(n_classes * 2, 100)
        
        if len(texts) < min_examples_for_split:
            if verbose:
                print(f"Small dataset ({len(texts)} < {min_examples_for_split}), training on all data without validation split")
            X_train, X_test = X, X
            yi_train, yi_test = y_intent, y_intent
            ym_train, ym_test = y_memory, y_memory
        else:
            # Normal split for larger datasets
            try:
                X_train, X_test, yi_train, yi_test, ym_train, ym_test = train_test_split(
                    X, y_intent, y_memory, test_size=test_size, random_state=42, stratify=y_intent
                )
            except ValueError:
                X_train, X_test, yi_train, yi_test, ym_train, ym_test = train_test_split(
                    X, y_intent, y_memory, test_size=test_size, random_state=42
                )
        
        if verbose:
            print(f"Training set: {len(X_train)}, Validation set: {len(X_test)}")
        
        # Train intent classifier
        if verbose:
            print("Training intent classifier...")
        self.intent_clf = LogisticRegression(
            max_iter=1000,
            multi_class="multinomial",
            class_weight="balanced"
        )
        self.intent_clf.fit(X_train, yi_train)
        
        # Train memory classifier
        if verbose:
            print("Training memory classifier...")
        self.memory_clf = LogisticRegression(
            max_iter=1000,
            multi_class="multinomial",
            class_weight="balanced"
        )
        self.memory_clf.fit(X_train, ym_train)
        
        self.is_trained = True
        
        # Evaluate (will be same as training for small datasets)
        intent_pred = self.intent_clf.predict(X_test)
        memory_pred = self.memory_clf.predict(X_test)
        
        intent_acc = (intent_pred == yi_test).mean()
        memory_acc = (memory_pred == ym_test).mean()
        
        if verbose:
            print(f"\n=== Training Complete ===")
            print(f"Intent Accuracy: {intent_acc:.2%}")
            print(f"Memory Accuracy: {memory_acc:.2%}")
            if len(texts) < min_examples_for_split:
                print("Note: Accuracy is on training data (no separate validation set)")
        
        return {
            "intent_accuracy": intent_acc,
            "memory_accuracy": memory_acc,
            "n_train": len(X_train),
            "n_test": len(X_test)
        }
    
    def predict(self, text: str) -> Dict:
        """
        Predict intent and memory target for a single text.
        
        Returns:
            {
                "intent": str,
                "intent_confidence": float,
                "memory_target": str,
                "memory_confidence": float,
                "is_confident": bool
            }
        """
        if not self.is_trained:
            # Fallback to rule-based
            return self._fallback_predict(text)
        
        # Get embedding
        X = embed(text)
        
        # Intent prediction
        intent_probs = self.intent_clf.predict_proba(X)[0]
        intent_idx = np.argmax(intent_probs)
        intent = self.intent_encoder.inverse_transform([intent_idx])[0]
        intent_conf = intent_probs[intent_idx]
        
        # Memory prediction
        memory_probs = self.memory_clf.predict_proba(X)[0]
        memory_idx = np.argmax(memory_probs)
        memory = self.memory_encoder.inverse_transform([memory_idx])[0]
        memory_conf = memory_probs[memory_idx]
        
        # Confidence check
        is_confident = intent_conf >= CONFIDENCE_THRESHOLD
        
        # If not confident, default to chitchat/none
        if not is_confident:
            intent = "chitchat"
            memory = "none"
        
        return {
            "intent": intent,
            "intent_confidence": float(intent_conf),
            "memory_target": memory,
            "memory_confidence": float(memory_conf),
            "is_confident": is_confident
        }
    
    def _fallback_predict(self, text: str) -> Dict:
        """Rule-based fallback when model not trained."""
        text_lower = text.lower().strip()
        
        # Simple keyword matching
        if any(w in text_lower for w in ["hi", "hello", "hey", "morning"]):
            return {"intent": "greeting", "intent_confidence": 0.8, "memory_target": "none", "memory_confidence": 1.0, "is_confident": True}
        
        if any(w in text_lower for w in ["thank", "thanks"]):
            return {"intent": "thanks", "intent_confidence": 0.8, "memory_target": "none", "memory_confidence": 1.0, "is_confident": True}
        
        if any(op in text_lower for op in ["+", "-", "*", "/", "plus", "minus", "times", "divided"]):
            return {"intent": "math", "intent_confidence": 0.8, "memory_target": "none", "memory_confidence": 1.0, "is_confident": True}
        
        if text_lower.startswith(("my ", "i'm ", "i am ", "my name")):
            return {"intent": "profile_store", "intent_confidence": 0.7, "memory_target": "sem", "memory_confidence": 0.7, "is_confident": True}
        
        if text_lower.startswith(("what is my", "what's my", "do i")):
            return {"intent": "profile_recall", "intent_confidence": 0.7, "memory_target": "sem", "memory_confidence": 0.7, "is_confident": True}
        
        return {"intent": "unknown", "intent_confidence": 0.3, "memory_target": "none", "memory_confidence": 1.0, "is_confident": False}
    
    def save(self, path: str = None):
        """Save trained classifier to disk."""
        if path is None:
            path = CLASSIFIER_PATH
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "wb") as f:
            pickle.dump({
                "intent_clf": self.intent_clf,
                "memory_clf": self.memory_clf,
                "intent_encoder": self.intent_encoder,
                "memory_encoder": self.memory_encoder,
                "is_trained": self.is_trained
            }, f)
        
        print(f"Classifier saved to {path}")
    
    def load(self, path: str = None) -> bool:
        """Load trained classifier from disk."""
        if path is None:
            path = CLASSIFIER_PATH
        
        if not os.path.exists(path):
            print(f"No trained model found at {path}")
            return False
        
        with open(path, "rb") as f:
            data = pickle.load(f)
        
        self.intent_clf = data["intent_clf"]
        self.memory_clf = data["memory_clf"]
        self.intent_encoder = data["intent_encoder"]
        self.memory_encoder = data["memory_encoder"]
        self.is_trained = data["is_trained"]
        
        print(f"Classifier loaded from {path}")
        return True


# Global singleton
_classifier = None


def get_classifier() -> NLUClassifier:
    """Get or create the global classifier instance."""
    global _classifier
    
    if _classifier is None:
        _classifier = NLUClassifier()
        _classifier.load()  # Try to load pre-trained model
    
    return _classifier
