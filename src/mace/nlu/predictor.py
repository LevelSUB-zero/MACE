"""
NLU Predictor - Unified Interface

Provides a single entry point for NLU predictions.
Uses ParserNLU (Behavior Shaping Model) as primary with keyword classifier fallback.
"""
from typing import Dict, Any, Optional
from .classifier import get_classifier
from .config import INTENT_TO_MEMORY

class NLUPredictor:
    """
    Unified NLU interface for the MACE system.
    
    Primary: ParserNLU (Generative Behavior Shaping Model)
    Fallback: Keyword classifier (when model fails or is uncertain)
    """
    
    def __init__(self, use_parser: bool = True):
        """Initialize predictor."""
        self._use_parser = use_parser
        self._parser_nlu = None
        self._classifier = None  # Lazy loaded
        print(f"✅ NLUPredictor initialized (Parser: {use_parser})")
    
    @property
    def classifier(self):
        if self._classifier is None:
            self._classifier = get_classifier()
        return self._classifier

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Unified prediction interface.
        buffer -> ParserNLU -> Keyword (fallback)
        """
        result = None

        # 1. Primary: Parser NLU
        if self._use_parser:
            try:
                if self._parser_nlu is None:
                    from .parser_nlu import ParserNLU
                    self._parser_nlu = ParserNLU()
                
                # The parser handles its own errors internally 
                # but might return "unknown" intent or None on failure
                result = self._parser_nlu.predict(text)
                
            except Exception as e:
                print(f"[NLU] ParserNLU failed, falling back to keyword: {e}")
                result = None

        # Check if parser failed effectively (unknown/low confidence)
        parser_failed = (result is None) or (result.get("intent") == "unknown")

        # 2. Fallback: Keyword Classifier
        if parser_failed:
            pred = self.classifier.predict(text)
            
            # Construct standard result from classifier output
            result = {
                "text": text,
                "intent": pred["intent"],
                "intent_confidence": pred["confidence"],
                "memory_type": pred["memory_target"],
                "complexity": "atomic", 
                "entities": {},
                "_source": "keyword"
            }
        
        # 3. Final Normalization & Logic
        # Ensure robust structure
        intent = result.get("intent", "unknown")
        memory_type = result.get("memory_type", "none")
        
        # Check if this is a rejection intent (chitchat, etc) that shouldn't be stored
        # Unless complexity requires it
        is_rejection = intent in {"chitchat", "greeting", "thanks", "gibberish", "unknown"}
        should_store = (memory_type != "none") and (not is_rejection)
        
        result.update({
            "should_store": should_store,
            "text": text  # Ensure text fits
        })
        
        return result

# Global singleton
_predictor = None

def get_predictor() -> NLUPredictor:
    """Get or create the global predictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = NLUPredictor()
    return _predictor
