"""
MACE NLU Training Data Generator

Uses Gemini to generate curriculum-based training data with strict schema validation.
Validates against MemoryAction.json before storing.

Usage:
    # Set your API key first
    set GOOGLE_API_KEY=your_key_here
    
    python -m mace.nlu.generate_data
"""
import json
import time
import os
import sys

try:
    from jsonschema import validate, ValidationError
except ImportError:
    print("Installing jsonschema...")
    os.system("pip install jsonschema")
    from jsonschema import validate, ValidationError

# ==========================================
# 1. CONFIGURATION
# ==========================================

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
SCHEMA_PATH = os.path.join(BASE_DIR, "schemas", "definitions", "MemoryAction.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "nlu", "generated_training_data.jsonl")

# Curriculum: (Level + Persona, Number of batches of 10 examples)
# Persona injection for diverse, real-world training data
CURRICULUM = [
    # === LEVEL 1: ATOMIC - Multiple Personas ===
    ("LEVEL 1: ATOMIC - Persona: Polite & Formal (Please do X, proper grammar)", 3),
    ("LEVEL 1: ATOMIC - Persona: Lazy Teenager (lowercase, slang, no punctuation, 'u', 'r', 'tmrw')", 3),
    ("LEVEL 1: ATOMIC - Persona: Stressed Boss (short, direct, imperative, dropping articles)", 3),
    ("LEVEL 1: ATOMIC - Persona: Non-Native Speaker (minor grammar errors, simple vocabulary)", 2),
    
    # === LEVEL 2: SEQUENTIAL - Multiple Personas ===
    ("LEVEL 2: SEQUENTIAL - Persona: Verbose Planner (detailed, 'first...then...finally')", 2),
    ("LEVEL 2: SEQUENTIAL - Persona: Rushed Professional (dropping pronouns, 'Meeting at 5, email Bob')", 2),
    ("LEVEL 2: SEQUENTIAL - Persona: Casual Friend (relaxed, 'oh and also', 'btw')", 2),
    
    # === LEVEL 3: CONDITIONAL - Multiple Personas ===
    ("LEVEL 3: CONDITIONAL - Persona: Software Engineer (precise, logical, 'if X then Y')", 2),
    ("LEVEL 3: CONDITIONAL - Persona: Forgetful User (uses 'um', 'uh', 'maybe', 'I think')", 2),
    ("LEVEL 3: CONDITIONAL - Persona: Busy Parent (multitasking, quick, 'when I get home')", 2),
    
    # === LEVEL 4: CORRECTION & META - Multiple Personas ===
    ("LEVEL 4: CORRECTION - Persona: Frustrated User (correcting impatiently, 'No, not that!')", 2),
    ("LEVEL 4: CORRECTION - Persona: Apologetic User (polite correction, 'sorry, I meant...')", 2),
    ("LEVEL 4: META - Persona: Curious User (asking why, 'how did you know that?')", 2),
    
    # === LEVEL 5: REFERENCE_HEAVY - Multiple Personas ===
    ("LEVEL 5: REFERENCE_HEAVY - Persona: Context-Heavy Speaker (lots of 'it', 'that', 'the other one')", 2),
    ("LEVEL 5: REFERENCE_HEAVY - Persona: Vague User (pointing, 'put that thing there')", 2),
    
    # === LEVEL 6: HARD NEGATIVES - Multiple Personas ===
    ("LEVEL 6: HARD NEGATIVES - Persona: Chatty User (small talk, opinions, 'I think...', 'you know...'). CRITICAL: These are rejection examples that should NOT be stored. complexity=atomic, memory_type=none, entities={}", 3),
    ("LEVEL 6: HARD NEGATIVES - Persona: Random Thoughts (incomplete sentences, 'hmm', 'nevermind'). CRITICAL: These are rejection examples. complexity=atomic, memory_type=none, entities={}", 3),
    ("LEVEL 6: HARD NEGATIVES - Persona: Math/Calculation requests ('what is 5+3?', 'calculate...'). CRITICAL: root_intent=math, complexity=atomic, memory_type=none, entities={}", 2),
]

# ==========================================
# 2. LOAD THE STRICT SCHEMA FROM FILE
# ==========================================
def load_schema():
    """Load the MemoryAction.json schema."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

MACE_SCHEMA = load_schema()

# ==========================================
# 3. THE MASTER PROMPT
# ==========================================
MASTER_PROMPT = """
*** SYSTEM PROMPT START ***
**Role:**
You are a Synthetic Data Generator for MACE (Memory for AI Cognitive Engines).
Your goal is to generate 10 high-quality training examples that STRICTLY VALIDATE against the provided JSON Schema.

**CRITICAL RULES:**
1. Output ONLY a JSON array of 10 objects. No markdown, no explanations.
2. Each object MUST validate against the schema.
3. `additionalProperties: false` means NO extra fields allowed.
4. Match `complexity` to the correct data shape:
   - atomic → requires `entities`, forbids `structure` and `steps`
   - conditional → requires `structure` with `trigger` and `action`
   - compound → requires `steps` array
   - update → requires `structure` with `operation`, `target_fact`, `new_value`
   - meta → requires `structure` with `query_type`
   - reference_heavy → requires `structure` with `object_ref`, `resolution_strategy`

**Target JSON Schema:**
{{SCHEMA_PLACEHOLDER}}

--------------------------------------------------------------------------------
**CURRENT GENERATION TASK:**
Generate **10 examples** strictly following the constraints of: **{{CURRENT_LEVEL}}**
--------------------------------------------------------------------------------

**Level Definitions:**

* **LEVEL 1: ATOMIC (Single Action)**
    * `complexity` = "atomic"
    * Use `entities` object (key-value pairs, values must be string/integer/boolean)
    * NO `structure`, NO `steps`
    * Include: profile_store, preference_store, contact_store, fact_teach, task_start, state_inform
    * Include 2 rejection examples (greeting, chitchat, thanks) with `entities: {}`

* **LEVEL 2: SEQUENTIAL (Multi-Step)**
    * `complexity` = "compound", `root_intent` = "sequence"
    * Use `steps` array (each step has `order`, `intent`, optional `memory_target`, `entities`)
    * NO `structure`
    * Include 2 rejection examples (rambling stories) with `memory_type: "none"`

* **LEVEL 3: CONDITIONAL (Trigger-Action)**
    * `complexity` = "conditional", `root_intent` = "automation_set"
    * Use `structure` with `trigger` and `action` (each has `intent` and `entities`)
    * NO `steps`
    * Include 2 rejection examples (wondering, hypotheticals)

* **LEVEL 4: CORRECTION & META (Complex)**
    * For CORRECTIONS: `complexity` = "update", `root_intent` = "fact_correction"
      * `structure` needs: `operation`, `target_fact` (with `attribute`), `new_value`
    * For META: `complexity` = "meta", `root_intent` = "explainability_request"
      * `structure` needs: `query_type` (source_trace|confidence|reasoning|history)
    * Include 2 rejection examples (self-cancellation like "Wait, nevermind")

* **LEVEL 5: REFERENCE_HEAVY (CWM)**
    * `complexity` = "reference_heavy", `memory_type` = "cwm"
    * `structure` needs: `object_ref`, `resolution_strategy`
    * Use pronouns: "it", "that", "this", "the other one"
    * root_intent: context_refer, item_move, clarification

* **LEVEL 6: HARD NEGATIVES (Rejections)**
    * `complexity` = "atomic", `memory_type` = "none"
    * `entities` = {}
    * root_intent: chitchat, greeting, thanks, gibberish, math, command_nav, unknown
    * Generate diverse rejection examples that should NOT be stored in memory

**OUTPUT FORMAT:**
Return ONLY a valid JSON array like:
[
  {"text": "...", "root_intent": "...", "memory_type": "...", "complexity": "...", ...},
  ...
]

*** SYSTEM PROMPT END ***
"""

# ==========================================
# 4. OLLAMA LLM INTERFACE
# ==========================================
OLLAMA_HOST = "https://918e-34-125-117-156.ngrok-free.app"
OLLAMA_MODEL = "qwen2.5:14b"

def query_llm(prompt_text, use_demo=False):
    """
    Sends the prompt to Ollama via external host.
    """
    if use_demo:
        print(" [DEMO MODE] ", end="")
        time.sleep(0.5)
        return json.dumps([
            {
                "text": "My name is Alice",
                "root_intent": "profile_store",
                "memory_type": "sem",
                "complexity": "atomic",
                "entities": {"attribute": "name", "value": "Alice"}
            }
        ])
    
    import requests
    
    url = f"{OLLAMA_HOST}/api/generate"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt_text,
        "stream": False,
        "options": {
            "temperature": 0.8
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true"
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    
    result = response.json()
    return result.get("response", "")

# ==========================================
# 5. VALIDATION
# ==========================================
def validate_example(example):
    """Validate a single example against the schema."""
    try:
        validate(instance=example, schema=MACE_SCHEMA)
        return True, None
    except ValidationError as e:
        return False, f"{e.message} at {list(e.absolute_path)}"

# ==========================================
# 6. MAIN EXECUTION
# ==========================================
def main(demo_mode=False):
    dataset = []
    schema_string = json.dumps(MACE_SCHEMA, indent=2)
    
    print("=" * 60)
    print("MACE NLU Training Data Generator")
    print("=" * 60)
    print(f"Schema: {SCHEMA_PATH}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Mode: {'DEMO' if demo_mode else f'LIVE (Ollama {OLLAMA_MODEL})'}")
    print(f"Curriculum: {len(CURRICULUM)} levels")
    print()

    stats = {"generated": 0, "valid": 0, "invalid": 0}

    for level_name, num_batches in CURRICULUM:
        print(f"\n>>> {level_name}")
        
        # Prepare the prompt
        prompt_with_schema = MASTER_PROMPT.replace("{{SCHEMA_PLACEHOLDER}}", schema_string)
        final_prompt = prompt_with_schema.replace("{{CURRENT_LEVEL}}", level_name)
        
        for i in range(num_batches):
            try:
                print(f"   Batch {i+1}/{num_batches}...", end="", flush=True)
                
                # A. Get raw text from LLM
                raw_response = query_llm(final_prompt, use_demo=demo_mode)
                
                # B. Parse JSON
                clean_json = raw_response.replace("```json", "").replace("```", "").strip()
                
                batch_data = json.loads(clean_json)
                if isinstance(batch_data, dict) and "examples" in batch_data:
                    batch_data = batch_data["examples"]
                
                if not isinstance(batch_data, list):
                    batch_data = [batch_data]

                stats["generated"] += len(batch_data)

                # C. Validate against Schema
                valid_items = []
                invalid_count = 0
                for item in batch_data:
                    is_valid, error = validate_example(item)
                    if is_valid:
                        item['_source'] = level_name
                        valid_items.append(item)
                        stats["valid"] += 1
                    else:
                        invalid_count += 1
                        stats["invalid"] += 1
                        if invalid_count <= 1:  # Only show first error
                            print(f" [INVALID: {error[:50]}...] ", end="")
                
                dataset.extend(valid_items)
                print(f" +{len(valid_items)} valid" + (f", -{invalid_count} invalid" if invalid_count else ""))
                
                # Rate limit
                if not demo_mode:
                    time.sleep(2)

            except json.JSONDecodeError as e:
                print(f" [JSON ERROR: {e}]")
            except Exception as e:
                print(f" [ERROR: {str(e)[:50]}]")

    # Append to JSONL (use 'a' mode to add to existing data)
    print(f"\nAppending to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for item in dataset:
            # Remove internal metadata before saving
            item_clean = {k: v for k, v in item.items() if not k.startswith("_")}
            f.write(json.dumps(item_clean) + "\n")

    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Generated: {stats['generated']}")
    print(f"Valid:     {stats['valid']} ({100*stats['valid']/max(1,stats['generated']):.1f}%)")
    print(f"Invalid:   {stats['invalid']}")
    print(f"Saved to:  {OUTPUT_FILE}")

if __name__ == "__main__":
    # Check for demo mode flag
    demo = "--demo" in sys.argv or "-d" in sys.argv
    main(demo_mode=demo)
