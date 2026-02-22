"""
MACE Parser NLU Test
Verifies the Behavior Shaping Model integration.
"""
import sys
import json
import os

# Ensure src path is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mace.nlu.predictor import get_predictor

def main():
    print("=" * 80)
    print("MACE NLU - Parser Integration Test")
    print("=" * 80)
    
    predictor = get_predictor()
    
    tests = [
        "remind me to buy milk tomorrow",
        "what is 5 + 3",
        "calculate 100 divided by 4",
        "my name is Alice",
        "I hate spicy food",
        "if I say hello then reply hi",
        "what did I say about the project yesterday",
        "correction: my email is actually bob@gmail.com",
        "scroll down",
        "asdf jkl",
        "save this and email it to john",
    ]
    
    for text in tests:
        print(f"\n📝 '{text}'")
        try:
            result = predictor.predict(text)
            intent = result.get("intent", "UNKNOWN")
            conf = result.get("intent_confidence", 0.0)
            mem = result.get("memory_type", "-")
            source = result.get("_source", "?")
            
            icon = "✅" if conf > 0.8 else ("⚠️" if conf > 0.5 else "❌")
            print(f"   {icon} [{source}] {intent} ({conf:.0%}) -> {mem}")
            
            ents = result.get("entities", {})
            if ents:
                print(f"      Entities: {json.dumps(ents, indent=2)}")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

if __name__ == "__main__":
    main()
