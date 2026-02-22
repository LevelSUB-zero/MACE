"""
Constrained NLU Engine using Ollama + Gemma 3 1B + Few-Shot Prompting.

Strategy: Use a stock capable model with comprehensive prompt engineering
instead of a fragile fine-tuned model. The model is instructed via system
prompt + few-shot examples, and output is validated through a strict checker.

Reliability Layers:
1. System Prompt — Complete schema specification with rules & constraints
2. Few-Shot Examples — 7 examples covering every complexity type
3. Ollama format:"json" — Forces valid JSON token generation at decode time
4. Schema Validation — Validates fields, types, and enum values
5. Retry Loop — Up to MAX_RETRIES attempts before falling back
6. Keyword Fallback — Deterministic classifier as last resort
"""
import json
import requests
from typing import Dict, Optional

# =============================================================
# CONFIG
# =============================================================
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "gemma3:1b"  # Stock model, no fine-tuning needed
TIMEOUT = 60  # CPU inference is slower, give it time
MAX_RETRIES = 3  # Retry with validation feedback

# =============================================================
# VALID ENUMS (the source of truth)
# =============================================================
VALID_INTENTS = {
    "profile_store", "profile_recall", "preference_store", "preference_recall",
    "contact_store", "contact_recall", "fact_teach", "fact_correction",
    "task_start", "task_update", "task_status", "reminder_set",
    "automation_set", "state_inform", "context_refer", "clarification",
    "continuation", "history_recall", "history_search", "user_action_recall",
    "explainability_request", "sequence", "item_move", "math",
    "chitchat", "greeting", "thanks", "gibberish", "command_nav", "unknown"
}
VALID_MEMORY = {"wm", "cwm", "sem", "epi", "mixed", "none"}
VALID_COMPLEXITY = {"atomic", "conditional", "compound", "update", "meta", "reference_heavy"}
REJECTION_INTENTS = {"chitchat", "greeting", "thanks", "math", "gibberish", "unknown", "command_nav"}

# =============================================================
# FEW-SHOT EXAMPLES (one per complexity type)
# =============================================================
FEW_SHOT_EXAMPLES = [
    # ─── ATOMIC: Core memory intents ───
    # 1. profile_store
    {
        "input": "My name is Alice",
        "output": {
            "text": "My name is Alice",
            "root_intent": "profile_store",
            "memory_type": "sem",
            "complexity": "atomic",
            "entities": {"attribute": "name", "value": "Alice"}
        }
    },
    # 2. preference_store
    {
        "input": "I like horror movies",
        "output": {
            "text": "I like horror movies",
            "root_intent": "preference_store",
            "memory_type": "sem",
            "complexity": "atomic",
            "entities": {"attribute": "genre_preference", "value": "horror movies"}
        }
    },
    # 3. contact_store
    {
        "input": "John's phone number is 555-1234",
        "output": {
            "text": "John's phone number is 555-1234",
            "root_intent": "contact_store",
            "memory_type": "sem",
            "complexity": "atomic",
            "entities": {"person": "John", "attribute": "phone_number", "value": "555-1234"}
        }
    },
    # 4. fact_teach
    {
        "input": "The capital of France is Paris",
        "output": {
            "text": "The capital of France is Paris",
            "root_intent": "fact_teach",
            "memory_type": "sem",
            "complexity": "atomic",
            "entities": {"attribute": "capital", "value": "Paris", "topic": "France"}
        }
    },
    # 5. reminder_set
    {
        "input": "Remind me to buy milk tomorrow",
        "output": {
            "text": "Remind me to buy milk tomorrow",
            "root_intent": "reminder_set",
            "memory_type": "wm",
            "complexity": "atomic",
            "entities": {"task": "buy milk", "time": "tomorrow"}
        }
    },
    # 6. task_start
    {
        "input": "Start working on the presentation",
        "output": {
            "text": "Start working on the presentation",
            "root_intent": "task_start",
            "memory_type": "wm",
            "complexity": "atomic",
            "entities": {"task": "working on the presentation"}
        }
    },
    # 7. state_inform
    {
        "input": "I am feeling tired today",
        "output": {
            "text": "I am feeling tired today",
            "root_intent": "state_inform",
            "memory_type": "cwm",
            "complexity": "atomic",
            "entities": {"attribute": "emotion_state", "value": "tired"}
        }
    },
    # 8. history_recall
    {
        "input": "What did we talk about yesterday",
        "output": {
            "text": "What did we talk about yesterday",
            "root_intent": "history_recall",
            "memory_type": "epi",
            "complexity": "atomic",
            "entities": {"time": "yesterday"}
        }
    },
    # ─── ATOMIC: Rejection intents (memory_type=none) ───
    # 9. greeting
    {
        "input": "hey whats up",
        "output": {
            "text": "hey whats up",
            "root_intent": "greeting",
            "memory_type": "none",
            "complexity": "atomic",
            "entities": {}
        }
    },
    # 10. chitchat
    {
        "input": "tell me a joke",
        "output": {
            "text": "tell me a joke",
            "root_intent": "chitchat",
            "memory_type": "none",
            "complexity": "atomic",
            "entities": {}
        }
    },
    # 11. math
    {
        "input": "what is 5 + 3",
        "output": {
            "text": "what is 5 + 3",
            "root_intent": "math",
            "memory_type": "none",
            "complexity": "atomic",
            "entities": {}
        }
    },
    # 12. thanks
    {
        "input": "thanks for the help",
        "output": {
            "text": "thanks for the help",
            "root_intent": "thanks",
            "memory_type": "none",
            "complexity": "atomic",
            "entities": {}
        }
    },
    # 13. command_nav
    {
        "input": "scroll down",
        "output": {
            "text": "scroll down",
            "root_intent": "command_nav",
            "memory_type": "none",
            "complexity": "atomic",
            "entities": {}
        }
    },
    # 14. gibberish
    {
        "input": "asdf jkl qwerty",
        "output": {
            "text": "asdf jkl qwerty",
            "root_intent": "gibberish",
            "memory_type": "none",
            "complexity": "atomic",
            "entities": {}
        }
    },
    # ─── CONDITIONAL ───
    # 15. automation_set
    {
        "input": "If it rains tomorrow, remind me to take an umbrella",
        "output": {
            "text": "If it rains tomorrow, remind me to take an umbrella",
            "root_intent": "automation_set",
            "memory_type": "wm",
            "complexity": "conditional",
            "structure": {
                "trigger": {"intent": "weather_check", "entities": {"condition": "raining"}},
                "action": {"intent": "reminder_set", "entities": {"item": "umbrella"}}
            }
        }
    },
    # ─── UPDATE ───
    # 16. fact_correction
    {
        "input": "No wait, my email is bob@gmail.com not the other one",
        "output": {
            "text": "No wait, my email is bob@gmail.com not the other one",
            "root_intent": "fact_correction",
            "memory_type": "sem",
            "complexity": "update",
            "structure": {
                "operation": "overwrite",
                "target_fact": {"attribute": "email"},
                "new_value": "bob@gmail.com",
                "sentiment": "correction"
            }
        }
    },
    # ─── COMPOUND ───
    # 17. sequence
    {
        "input": "Save this file and email it to Bob",
        "output": {
            "text": "Save this file and email it to Bob",
            "root_intent": "sequence",
            "memory_type": "mixed",
            "complexity": "compound",
            "steps": [
                {"order": 1, "intent": "file_save", "entities": {"target": "current_file"}},
                {"order": 2, "intent": "email_send", "entities": {"recipient": "Bob"}}
            ]
        }
    },
    # ─── REFERENCE_HEAVY ───
    # 18. item_move (pronouns/context references)
    {
        "input": "put that in the other folder",
        "output": {
            "text": "put that in the other folder",
            "root_intent": "item_move",
            "memory_type": "cwm",
            "complexity": "reference_heavy",
            "entities": {"object_ref": "that", "target": "the other folder"}
        }
    },
    # ─── META ───
    # 19. explainability_request
    {
        "input": "Why did you think I liked comedy?",
        "output": {
            "text": "Why did you think I liked comedy?",
            "root_intent": "explainability_request",
            "memory_type": "sem",
            "complexity": "meta",
            "entities": {"query_type": "reasoning", "topic": "comedy preference"}
        }
    },
    # ─── ADDITIONAL COVERAGE (MEM-002) ───
    # 20. contact_store — "my friend X is a Y"
    {
        "input": "my friend John is a doctor",
        "output": {
            "text": "my friend John is a doctor",
            "root_intent": "contact_store",
            "memory_type": "sem",
            "complexity": "atomic",
            "entities": {"person": "John", "attribute": "role", "value": "doctor"}
        }
    },
    # 21. fact_teach — "remember that X is Y"
    {
        "input": "remember that the sun is a star",
        "output": {
            "text": "remember that the sun is a star",
            "root_intent": "fact_teach",
            "memory_type": "sem",
            "complexity": "atomic",
            "entities": {"attribute": "sun", "value": "a star"}
        }
    },
    # 22. profile_recall — "what is my X"
    {
        "input": "what is my name",
        "output": {
            "text": "what is my name",
            "root_intent": "profile_recall",
            "memory_type": "sem",
            "complexity": "atomic",
            "entities": {"attribute": "name"}
        }
    },
    # 23. profile_store — location variant
    {
        "input": "I live in Tokyo",
        "output": {
            "text": "I live in Tokyo",
            "root_intent": "profile_store",
            "memory_type": "sem",
            "complexity": "atomic",
            "entities": {"attribute": "location", "value": "Tokyo"}
        }
    },
    # 24. history_search — "what is X" (fact retrieval)
    {
        "input": "what is the sun",
        "output": {
            "text": "what is the sun",
            "root_intent": "history_search",
            "memory_type": "sem",
            "complexity": "atomic",
            "entities": {"attribute": "sun"}
        }
    },
    # 25. contact_recall — "who is X"
    {
        "input": "who is John",
        "output": {
            "text": "who is John",
            "root_intent": "contact_recall",
            "memory_type": "sem",
            "complexity": "atomic",
            "entities": {"person": "John"}
        }
    },
]

# =============================================================
# SYSTEM PROMPT — the "brain" of the NLU
# =============================================================
SYSTEM_PROMPT = """You are MACE-NLU, a deterministic Natural Language Understanding parser.
Your ONLY job is to parse user input into a single JSON object. You must NEVER output anything other than valid JSON.

## REQUIRED FIELDS (always present):
- "text": the original user input (string)
- "root_intent": one of the valid intents listed below (string)
- "memory_type": one of: "wm", "cwm", "sem", "epi", "mixed", "none" (string)
- "complexity": one of: "atomic", "conditional", "compound", "update", "meta", "reference_heavy" (string)

## CONDITIONAL FIELDS (based on complexity):
- For "atomic": include "entities" object with key-value pairs (e.g. {"attribute": "name", "value": "Alice"})
- For "conditional": include "structure" with "trigger" and "action" sub-objects
- For "compound": include "steps" array with ordered sub-intents
- For "update": include "structure" with "operation", "target_fact", "new_value"
- For "meta": include "entities" with "query_type"
- For "reference_heavy": include "entities" with "object_ref"

## VALID root_intent VALUES:
profile_store, profile_recall, preference_store, preference_recall,
contact_store, contact_recall, fact_teach, fact_correction,
task_start, task_update, task_status, reminder_set,
automation_set, state_inform, context_refer, clarification,
continuation, history_recall, history_search, user_action_recall,
explainability_request, sequence, item_move, math,
chitchat, greeting, thanks, gibberish, command_nav, unknown

## RULES:
1. Output ONLY a JSON object. No markdown, no explanation, no text before or after.
2. For chitchat/greeting/thanks/math/gibberish/unknown/command_nav: memory_type MUST be "none", entities MUST be {}
3. Pick the MOST SPECIFIC intent that matches the user's input.
4. "entities" keys should describe WHAT was extracted (e.g. "attribute", "value", "task", "time", "person", "location")"""


def _build_prompt(user_input: str) -> str:
    """Build few-shot prompt with examples."""
    parts = ["EXAMPLES:", ""]

    for ex in FEW_SHOT_EXAMPLES:
        parts.append(f'Input: "{ex["input"]}"')
        parts.append(f"Output: {json.dumps(ex['output'])}")
        parts.append("")

    parts.append(f'NOW PARSE THIS:')
    parts.append(f'Input: "{user_input}"')
    parts.append("Output:")

    return "\n".join(parts)


def _validate_schema(result: Dict) -> tuple[bool, str]:
    """
    Strict schema validation. Returns (is_valid, error_message).
    This is the output checker — only valid output passes.
    """
    # Check required fields exist
    for field in ["text", "root_intent", "memory_type", "complexity"]:
        if field not in result:
            return False, f"Missing required field: {field}"

    # Check enum values
    if result["root_intent"] not in VALID_INTENTS:
        return False, f"Invalid root_intent: {result['root_intent']}. Must be one of: {', '.join(sorted(VALID_INTENTS))}"

    if result["memory_type"] not in VALID_MEMORY:
        return False, f"Invalid memory_type: {result['memory_type']}. Must be one of: {', '.join(VALID_MEMORY)}"

    if result["complexity"] not in VALID_COMPLEXITY:
        return False, f"Invalid complexity: {result['complexity']}. Must be one of: {', '.join(VALID_COMPLEXITY)}"

    # Rejection intents must have memory_type=none
    if result["root_intent"] in REJECTION_INTENTS and result["memory_type"] != "none":
        return False, f"Intent '{result['root_intent']}' must have memory_type='none'"

    # Complexity-specific checks
    complexity = result["complexity"]
    if complexity == "atomic" and "entities" not in result:
        return False, "Atomic complexity requires 'entities' field"
    if complexity == "conditional" and "structure" not in result:
        return False, "Conditional complexity requires 'structure' field"
    if complexity == "compound" and "steps" not in result:
        return False, "Compound complexity requires 'steps' field"
    if complexity == "update" and "structure" not in result:
        return False, "Update complexity requires 'structure' field"

    return True, ""


def _normalize_result(result: Dict, user_input: str) -> Dict:
    """Normalize and fix minor issues in validated output."""
    # Always override text with actual input
    result["text"] = user_input

    # Enforce rejection rules
    if result["root_intent"] in REJECTION_INTENTS:
        result["memory_type"] = "none"
        result["complexity"] = "atomic"
        result["entities"] = {}
        result.pop("structure", None)
        result.pop("steps", None)

    # Ensure entities exists for atomic
    if result["complexity"] == "atomic" and "entities" not in result:
        result["entities"] = {}

    return result


def _extract_json(text: str) -> Optional[Dict]:
    """Extract the first valid JSON object from text, handling nested braces."""
    start = text.find('{')
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    next_start = text.find('{', i + 1)
                    if next_start != -1:
                        return _extract_json(text[next_start:])
                    return None
    return None


def query_ollama(user_input: str, host: str = None, model: str = None) -> Optional[Dict]:
    """
    Query Ollama with retry loop and validation.
    
    Attempts up to MAX_RETRIES times. Each failed validation feeds
    the error back into the next attempt for self-correction.
    """
    host = host or OLLAMA_HOST
    model = model or OLLAMA_MODEL
    prompt = _build_prompt(user_input)
    
    last_error = ""
    
    for attempt in range(MAX_RETRIES):
        # Add correction hint on retry
        current_prompt = prompt
        if last_error:
            current_prompt += f"\n\nYour previous output was invalid: {last_error}. Fix it and try again."

        payload = {
            "model": model,
            "system": SYSTEM_PROMPT,
            "prompt": current_prompt,
            "stream": False,
            "format": "json",  # Gemma 3 supports native JSON mode
            "options": {
                "temperature": 0,
                "num_predict": 512,
                "stop": ["\nInput:", "\nNOW PARSE", "```"],
            }
        }

        try:
            resp = requests.post(
                f"{host}/api/generate",
                json=payload,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "")

            # Try parsing JSON
            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                result = _extract_json(raw)
            
            if result is None:
                last_error = f"No valid JSON found in response: {raw[:100]}"
                print(f"[NLU] Attempt {attempt+1}/{MAX_RETRIES}: {last_error}")
                continue

            # Validate against schema
            is_valid, error = _validate_schema(result)
            if not is_valid:
                last_error = error
                print(f"[NLU] Attempt {attempt+1}/{MAX_RETRIES}: Schema validation failed: {error}")
                continue

            # Normalize and return
            result = _normalize_result(result, user_input)
            if attempt > 0:
                print(f"[NLU] ✅ Succeeded on attempt {attempt+1}")
            return result

        except requests.exceptions.ConnectionError:
            print(f"[NLU] Ollama not running at {host}")
            return None
        except requests.exceptions.Timeout:
            print(f"[NLU] Ollama timeout after {TIMEOUT}s (attempt {attempt+1})")
            last_error = "Timeout"
            continue
        except Exception as e:
            print(f"[NLU] Ollama error: {e}")
            return None

    print(f"[NLU] ❌ All {MAX_RETRIES} attempts failed. Last error: {last_error}")
    return None


def parse(user_input: str, host: str = None, model: str = None) -> Dict:
    """
    Main entry point: Parse user input into structured NLU output.
    
    Tries Ollama first (with retries + validation), falls back to keyword classifier.
    """
    # Layer 1-4: Few-shot + JSON mode + Schema validation + Retry
    result = query_ollama(user_input, host, model)

    if result:
        result["_source"] = "ollama"
        return result

    # Fallback: keyword classifier
    try:
        from .classifier import get_classifier
        classifier = get_classifier()
        pred = classifier.predict(user_input)

        return {
            "text": user_input,
            "root_intent": pred.get("intent", "unknown"),
            "memory_type": pred.get("memory_target", "none"),
            "complexity": "atomic",
            "entities": {},
            "_source": "keyword_fallback",
        }
    except Exception:
        return {
            "text": user_input,
            "root_intent": "unknown",
            "memory_type": "none",
            "complexity": "atomic",
            "entities": {},
            "_source": "error_fallback",
        }


# =============================================================
# CLI TEST
# =============================================================
if __name__ == "__main__":
    test_inputs = [
        "my name is bob",
        "yo remind me 2 get milk tmrw",
        "remind me to call mom when i get home",
        "no wait, my email is bob@gmail.com not the other one",
        "hey whats up",
        "what is 5 + 3",
        "save this and email it to alice",
        "put that in the other folder",
        "I like horror movies",
        "why did you think I liked comedy?",
    ]

    print("=" * 60)
    print("MACE NLU — Gemma 3 1B + Prompt Engineering Test")
    print("=" * 60)

    passed = 0
    failed = 0

    for inp in test_inputs:
        result = parse(inp)
        source = result.pop("_source", "?")
        valid = result.get("root_intent") != "unknown"

        icon = "✅" if valid else "❌"
        if valid:
            passed += 1
        else:
            failed += 1

        print(f"\n{icon} [{source}] \"{inp}\"")
        print(f"   → {json.dumps(result, indent=2)[:300]}")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{passed + failed} passed")
    print(f"{'=' * 60}")
