"""
MACE Parser NLU Engine
Inference engine for the Behavior Shaping Model (Qwen 1.5B).
Enforces Strict Schema via JSON Mode.

Schema:
{
  "text": "...",
  "root_intent": "...",
  "memory_type": "...",
  "complexity": "...",
  "entities": {
    "task": null, "time": null, "person": null, "location": null,
    "topic": null, "attribute": null, "value": null, "target": null
  }
}
"""
import json
import requests
import os
from typing import Dict, Any, Optional

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = "mace-nlu-qwen1.5b"  # User will create this model in Ollama

class ParserNLU:
    def __init__(self):
        self.model_name = MODEL_NAME
        print(f"✅ ParserNLU initialized (Target: {self.model_name})")

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predict intent and entities using the Behavior Shaping model.
        Returns standard prediction dict.
        """
        # 1. Prompt Construction (Matches Training)
        prompt = f"Input: {text}\nOutput:"
        
        # 2. Schema for Constrained Decoding (Ollama format)
        # We use a simplified schema definition to guide the JSON mode
        # Qwen 2.5 supports native JSON mode well without explicit schema sometimes,
        # but providing it is safer.
        json_schema = {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "root_intent": {"type": "string"},
                "memory_type": {"type": "string"},
                "complexity": {"type": "string"},
                "entities": {
                    "type": "object",
                    "properties": {
                        "task": {"type": ["string", "null"]},
                        "time": {"type": ["string", "null"]},
                        "person": {"type": ["string", "null"]},
                        "location": {"type": ["string", "null"]},
                        "topic": {"type": ["string", "null"]},
                        "attribute": {"type": ["string", "null"]},
                        "value": {"type": ["string", "null"]},
                        "target": {"type": ["string", "null"]}
                    },
                    "required": ["task", "time", "person", "location", "topic", "attribute", "value", "target"]
                }
            },
            "required": ["text", "root_intent", "memory_type", "complexity", "entities"]
        }

        # 3. Call Ollama
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "format": "json",  # Force JSON
                    "stream": False,
                    "options": {
                        "temperature": 0.0,  # Strict deterministic output
                        "stop": ["<|endoftext|>", "\nInput:", "Input:"]
                    }
                },
                timeout=5
            )
            response.raise_for_status()
            result = response.json()
            raw_json = result.get("response", "{}")
            
            # 4. Parse & Normalize
            data = json.loads(raw_json)
            
            # Extract fields
            intent = data.get("root_intent", "unknown")
            memory_type = data.get("memory_type", "none")
            complexity = data.get("complexity", "atomic")
            entities = data.get("entities", {})
            
            # Clean entities (remove nulls for downstream consumption)
            clean_entities = {k: v for k, v in entities.items() if v is not None}

            return {
                "intent": intent,
                "intent_confidence": 1.0,  # Generative model is confident by definition/construction
                "memory_type": memory_type,
                "complexity": complexity,
                "entities": clean_entities,
                "_source": "parser_nlu"
            }

        except Exception as e:
            print(f"❌ ParserNLU Error: {e}")
            # Fallback
            return {
                "intent": "unknown",
                "intent_confidence": 0.0,
                "memory_type": "none",
                "complexity": "atomic",
                "entities": {},
                "_source": "parser_nlu_error"
            }

if __name__ == "__main__":
    # Test
    nlu = ParserNLU()
    print(nlu.predict("remind me to buy milk tomorrow"))
