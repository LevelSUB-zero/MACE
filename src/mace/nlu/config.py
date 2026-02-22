"""
Hierarchical NLU Configuration

Defines the schema for complex, recursive intent structures that handle:
- Atomic commands (simple)
- Conditional (trigger + action)
- Sequential (multi-step)
- Corrections (semantic updates)
- Meta-cognition (reasoning about reasoning)
- Reference resolution (CWM)
"""
import os

# =============================================================================
# ROOT INTENT CLASSES
# =============================================================================

ROOT_INTENTS = [
    # --- Semantic Memory (Permanent Facts & Preferences) ---
    "profile_store",       # "My birthday is June 15th"
    "profile_recall",      # "When is my birthday?"
    "preference_store",    # "I hate spicy food"
    "preference_recall",   # "Do I like sushi?"
    "contact_store",       # "Bob is my coworker"
    "contact_recall",      # "Who is Bob?"
    "fact_teach",          # "The gate code is 1234"
    "fact_correction",     # "No, I moved to NYC" [COMPLEX: update]

    # --- Working Memory (Current Tasks & Status) ---
    "task_start",          # "I'm starting to cook dinner"
    "task_update",         # "Finished chopping the onions"
    "task_status",         # "What was I doing?"
    "reminder_set",        # "Remind me in 10 minutes" [COMPLEX: conditional]
    "automation_set",      # "Remind me to X when Y" [COMPLEX: trigger+action]
    "state_inform",        # "I'm feeling tired"

    # --- Contextual Working Memory (Immediate Conversation) ---
    "context_refer",       # "Does it have a battery?" [COMPLEX: reference]
    "item_move",           # "Put that in the other folder" [COMPLEX: reference]
    "clarification",       # "What did you mean?"
    "continuation",        # "And then what?"

    # --- Episodic Memory (Interaction History) ---
    "history_recall",      # "What did we discuss yesterday?"
    "history_search",      # "Did I mention a book last week?"
    "user_action_recall",  # "When was the last time I went running?"
    "explainability_request",  # "Why did you think I liked X?" [COMPLEX: meta]

    # --- Compound / Sequential ---
    "sequence",            # "Save this and email it to Bob" [COMPLEX: compound]

    # --- Operational / No-Store (Rejection Classes) ---
    "math",                # "What is 55 * 3?"
    "chitchat",            # "How are you doing?"
    "greeting",            # "Hello there"
    "thanks",              # "Thank you"
    "gibberish",           # "asdf jkl"
    "command_nav",         # "Scroll down"
    "unknown",             # Fallback
]

# =============================================================================
# MEMORY TARGET CLASSES
# =============================================================================

MEMORY_TYPES = [
    "wm",       # Working Memory - volatile, current request
    "cwm",      # Contextual WM - session conversation buffer
    "sem",      # Semantic Memory - permanent facts & preferences
    "epi",      # Episodic Memory - interaction history logs
    "mixed",    # Multiple memory types involved (compound intents)
    "none",     # No memory operation (rejection)
]

# =============================================================================
# COMPLEXITY TYPES
# =============================================================================

COMPLEXITY_TYPES = [
    "atomic",           # Simple, flat intent (most common)
    "conditional",      # Trigger + Action (e.g., "when X, do Y")
    "compound",         # Sequential steps (e.g., "do X and Y")
    "update",           # Correction/overwrite (e.g., "no, actually...")
    "meta",             # Meta-cognition (e.g., "why did you think...")
    "reference_heavy",  # Heavy CWM reference resolution
]

# =============================================================================
# INTENT TO DEFAULT MEMORY MAPPING
# =============================================================================

INTENT_TO_MEMORY = {
    # Semantic
    "profile_store": "sem",
    "profile_recall": "sem",
    "preference_store": "sem",
    "preference_recall": "sem",
    "contact_store": "sem",
    "contact_recall": "sem",
    "fact_teach": "sem",
    "fact_correction": "sem",

    # Working Memory
    "task_start": "wm",
    "task_update": "wm",
    "task_status": "wm",
    "reminder_set": "wm",
    "automation_set": "wm",
    "state_inform": "wm",

    # Contextual Working Memory
    "context_refer": "cwm",
    "item_move": "cwm",
    "clarification": "cwm",
    "continuation": "cwm",

    # Episodic
    "history_recall": "epi",
    "history_search": "epi",
    "user_action_recall": "epi",
    "explainability_request": "epi",

    # Compound
    "sequence": "mixed",

    # Rejection
    "math": "none",
    "chitchat": "none",
    "greeting": "none",
    "thanks": "none",
    "gibberish": "none",
    "command_nav": "none",
    "unknown": "none",
}

# =============================================================================
# INTENT TO DEFAULT COMPLEXITY
# =============================================================================

INTENT_TO_COMPLEXITY = {
    "automation_set": "conditional",
    "fact_correction": "update",
    "sequence": "compound",
    "explainability_request": "meta",
    "context_refer": "reference_heavy",
    "item_move": "reference_heavy",
}
# All others default to "atomic"

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
MODEL_DIR = os.path.join(BASE_DIR, "models", "nlu")
DATA_DIR = os.path.join(BASE_DIR, "data", "nlu")
SCHEMA_PATH = os.path.join(BASE_DIR, "schemas", "definitions", "MemoryAction.json")

TRAINING_DATA_PATH = os.path.join(DATA_DIR, "training_data.jsonl")
CLASSIFIER_PATH = os.path.join(MODEL_DIR, "classifier.pkl")

# For generative model (T5/Llama)
GENERATIVE_MODEL = "google/flan-t5-base"  # Or local fine-tuned model
GENERATIVE_MODEL_PATH = os.path.join(MODEL_DIR, "nlu_generator")

# Thresholds
CONFIDENCE_THRESHOLD = 0.7
MIN_EXAMPLES_PER_CLASS = 50

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_default_memory(intent: str) -> str:
    """Get default memory target for an intent."""
    return INTENT_TO_MEMORY.get(intent, "none")

def get_default_complexity(intent: str) -> str:
    """Get default complexity type for an intent."""
    return INTENT_TO_COMPLEXITY.get(intent, "atomic")

def is_complex_intent(intent: str) -> bool:
    """Check if intent requires hierarchical parsing."""
    return intent in INTENT_TO_COMPLEXITY
