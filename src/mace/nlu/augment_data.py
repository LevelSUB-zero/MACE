"""
MACE NLU Data Augmentation — Fill missing/weak intent classes.

Adds hand-crafted examples for underrepresented intents.
Run: python -m mace.nlu.augment_data
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "nlu", "generated_training_data.jsonl")

# =================================================================
# Hand-crafted examples for missing/weak intents
# =================================================================
AUGMENTED = [
    # ===== MATH (0 examples) =====
    {"text": "what is 5 + 3", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "calculate 100 divided by 4", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "how much is 15% of 200", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "whats 7 times 8", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "12 minus 5", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "what is the square root of 144", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "9 * 6 =", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "can you do 35 plus 27", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "how many is 3 dozen", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "50 divided by 7", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "what does 2 to the power of 10 equal", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "99 minus 33", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "add 45 and 67", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "multiply 11 by 11", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "how much is a third of 90", "root_intent": "math", "memory_type": "none", "complexity": "atomic", "entities": {}},

    # ===== GIBBERISH (0 examples) =====
    {"text": "asdf jkl qwerty", "root_intent": "gibberish", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "hjkl zxcv bnm", "root_intent": "gibberish", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "aaa bbb ccc", "root_intent": "gibberish", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "lksjdflksj", "root_intent": "gibberish", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "qwertyuiop", "root_intent": "gibberish", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "fdjskl fdjskl fdjskl", "root_intent": "gibberish", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "...", "root_intent": "gibberish", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "xxx yyy zzz", "root_intent": "gibberish", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "123abc456def", "root_intent": "gibberish", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "blah blah blah", "root_intent": "gibberish", "memory_type": "none", "complexity": "atomic", "entities": {}},

    # ===== COMMAND_NAV (0 examples) =====
    {"text": "scroll down", "root_intent": "command_nav", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "go back", "root_intent": "command_nav", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "open settings", "root_intent": "command_nav", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "close this window", "root_intent": "command_nav", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "show me the menu", "root_intent": "command_nav", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "next page", "root_intent": "command_nav", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "go to home", "root_intent": "command_nav", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "refresh the page", "root_intent": "command_nav", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "zoom in", "root_intent": "command_nav", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "undo that", "root_intent": "command_nav", "memory_type": "none", "complexity": "atomic", "entities": {}},

    # ===== UNKNOWN (0 examples) =====
    {"text": "hmm", "root_intent": "unknown", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "i dont know", "root_intent": "unknown", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "never mind", "root_intent": "unknown", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "forget it", "root_intent": "unknown", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "ok whatever", "root_intent": "unknown", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "meh", "root_intent": "unknown", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "umm", "root_intent": "unknown", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "idk", "root_intent": "unknown", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "nah", "root_intent": "unknown", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "maybe later", "root_intent": "unknown", "memory_type": "none", "complexity": "atomic", "entities": {}},

    # ===== CONTINUATION (0 examples) =====
    {"text": "and then what", "root_intent": "continuation", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "go on", "root_intent": "continuation", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "tell me more", "root_intent": "continuation", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "what else", "root_intent": "continuation", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "continue", "root_intent": "continuation", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "keep going", "root_intent": "continuation", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "and", "root_intent": "continuation", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "what happened next", "root_intent": "continuation", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "so then", "root_intent": "continuation", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "anything else", "root_intent": "continuation", "memory_type": "cwm", "complexity": "atomic", "entities": {}},

    # ===== HISTORY_RECALL (0 examples) =====
    {"text": "what did we talk about yesterday", "root_intent": "history_recall", "memory_type": "epi", "complexity": "atomic", "entities": {}},
    {"text": "what did I say earlier", "root_intent": "history_recall", "memory_type": "epi", "complexity": "atomic", "entities": {}},
    {"text": "what was the last thing we discussed", "root_intent": "history_recall", "memory_type": "epi", "complexity": "atomic", "entities": {}},
    {"text": "remind me what I asked before", "root_intent": "history_recall", "memory_type": "epi", "complexity": "atomic", "entities": {}},
    {"text": "what did you tell me last time", "root_intent": "history_recall", "memory_type": "epi", "complexity": "atomic", "entities": {}},
    {"text": "can you repeat what I said", "root_intent": "history_recall", "memory_type": "epi", "complexity": "atomic", "entities": {}},
    {"text": "what was my first message", "root_intent": "history_recall", "memory_type": "epi", "complexity": "atomic", "entities": {}},
    {"text": "what happened in our last conversation", "root_intent": "history_recall", "memory_type": "epi", "complexity": "atomic", "entities": {}},
    {"text": "go back to what we were talking about", "root_intent": "history_recall", "memory_type": "epi", "complexity": "atomic", "entities": {}},
    {"text": "what did I tell you on monday", "root_intent": "history_recall", "memory_type": "epi", "complexity": "atomic", "entities": {"day": "monday"}},

    # ===== HISTORY_SEARCH (0 examples) =====
    {"text": "did I mention a book last week", "root_intent": "history_search", "memory_type": "epi", "complexity": "atomic", "entities": {"topic": "book", "time": "last week"}},
    {"text": "have I ever talked about cooking", "root_intent": "history_search", "memory_type": "epi", "complexity": "atomic", "entities": {"topic": "cooking"}},
    {"text": "did I say anything about travel", "root_intent": "history_search", "memory_type": "epi", "complexity": "atomic", "entities": {"topic": "travel"}},
    {"text": "when did I first mention alice", "root_intent": "history_search", "memory_type": "epi", "complexity": "atomic", "entities": {"person": "alice"}},
    {"text": "have we discussed this before", "root_intent": "history_search", "memory_type": "epi", "complexity": "atomic", "entities": {}},
    {"text": "search for when I talked about the project", "root_intent": "history_search", "memory_type": "epi", "complexity": "atomic", "entities": {"topic": "project"}},
    {"text": "find my message about the password", "root_intent": "history_search", "memory_type": "epi", "complexity": "atomic", "entities": {"topic": "password"}},
    {"text": "did I bring up the meeting", "root_intent": "history_search", "memory_type": "epi", "complexity": "atomic", "entities": {"topic": "meeting"}},
    {"text": "look for what I said about my car", "root_intent": "history_search", "memory_type": "epi", "complexity": "atomic", "entities": {"topic": "car"}},
    {"text": "when was the last time I mentioned gym", "root_intent": "history_search", "memory_type": "epi", "complexity": "atomic", "entities": {"topic": "gym"}},

    # ===== USER_ACTION_RECALL (0 examples) =====
    {"text": "when was the last time I went running", "root_intent": "user_action_recall", "memory_type": "epi", "complexity": "atomic", "entities": {"action": "running"}},
    {"text": "when did I last go to the gym", "root_intent": "user_action_recall", "memory_type": "epi", "complexity": "atomic", "entities": {"action": "gym"}},
    {"text": "how long since I called mom", "root_intent": "user_action_recall", "memory_type": "epi", "complexity": "atomic", "entities": {"action": "called mom"}},
    {"text": "did I water the plants today", "root_intent": "user_action_recall", "memory_type": "epi", "complexity": "atomic", "entities": {"action": "water the plants"}},
    {"text": "when did I last eat", "root_intent": "user_action_recall", "memory_type": "epi", "complexity": "atomic", "entities": {"action": "eat"}},
    {"text": "have I taken my pills today", "root_intent": "user_action_recall", "memory_type": "epi", "complexity": "atomic", "entities": {"action": "taken pills"}},
    {"text": "when was the last time I slept well", "root_intent": "user_action_recall", "memory_type": "epi", "complexity": "atomic", "entities": {"action": "slept well"}},
    {"text": "did I exercise yesterday", "root_intent": "user_action_recall", "memory_type": "epi", "complexity": "atomic", "entities": {"action": "exercise"}},
    {"text": "how many days since my last run", "root_intent": "user_action_recall", "memory_type": "epi", "complexity": "atomic", "entities": {"action": "run"}},
    {"text": "when did I finish that report", "root_intent": "user_action_recall", "memory_type": "epi", "complexity": "atomic", "entities": {"action": "finish report"}},

    # ===== PREFERENCE_RECALL (0 examples) =====
    {"text": "what is my favorite color", "root_intent": "preference_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "favorite color"}},
    {"text": "do I like sushi", "root_intent": "preference_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "sushi"}},
    {"text": "what kind of music do I prefer", "root_intent": "preference_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "music"}},
    {"text": "am I a morning person", "root_intent": "preference_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "morning person"}},
    {"text": "what movies do I like", "root_intent": "preference_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "movies"}},
    {"text": "whats my favorite food", "root_intent": "preference_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "food"}},
    {"text": "do I prefer coffee or tea", "root_intent": "preference_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "coffee or tea"}},
    {"text": "what genre do I read", "root_intent": "preference_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "genre"}},
    {"text": "what is my favorite animal", "root_intent": "preference_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "animal"}},
    {"text": "do I like spicy food", "root_intent": "preference_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "spicy food"}},

    # ===== TASK_UPDATE (0 examples) =====
    {"text": "finished chopping the onions", "root_intent": "task_update", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "chopping the onions", "status": "finished"}},
    {"text": "done with the first draft", "root_intent": "task_update", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "first draft", "status": "done"}},
    {"text": "I completed the workout", "root_intent": "task_update", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "workout", "status": "completed"}},
    {"text": "halfway through the report", "root_intent": "task_update", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "report", "status": "halfway"}},
    {"text": "just started cooking", "root_intent": "task_update", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "cooking", "status": "started"}},
    {"text": "I finished cleaning", "root_intent": "task_update", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "cleaning", "status": "finished"}},
    {"text": "still working on the presentation", "root_intent": "task_update", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "presentation", "status": "in progress"}},
    {"text": "almost done with laundry", "root_intent": "task_update", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "laundry", "status": "almost done"}},
    {"text": "cancelled the meeting", "root_intent": "task_update", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "meeting", "status": "cancelled"}},
    {"text": "paused the project for now", "root_intent": "task_update", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "project", "status": "paused"}},

    # ===== REMINDER_SET (only 10, need more) =====
    {"text": "remind me to call the doctor", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "call the doctor"}},
    {"text": "set a reminder for 3pm", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"time": "3pm"}},
    {"text": "remind me to take my medicine at 8", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "take medicine", "time": "8"}},
    {"text": "dont let me forget to buy groceries", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "buy groceries"}},
    {"text": "remind me about the dentist tomorrow", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "dentist", "time": "tomorrow"}},
    {"text": "set an alarm for the meeting", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "meeting"}},
    {"text": "remind me to water the plants", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "water plants"}},
    {"text": "hey remind me to pick up the kids at 4", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "pick up kids", "time": "4"}},
    {"text": "i need a reminder to pay rent", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "pay rent"}},
    {"text": "yo remind me 2 get milk tmrw", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "get milk", "time": "tomorrow"}},
    {"text": "remind me in 10 minutes", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"time": "10 minutes"}},
    {"text": "dont forget to email john", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "email john"}},
    {"text": "reminder to submit the assignment", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "submit assignment"}},
    {"text": "remind me to charge my phone", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "charge phone"}},
    {"text": "can you remind me to lock the door", "root_intent": "reminder_set", "memory_type": "wm", "complexity": "atomic", "entities": {"task": "lock the door"}},

    # ===== CHITCHAT (only 3) =====
    {"text": "how are you doing", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "nice weather today", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "what do you think about AI", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "thats funny", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "lol", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "haha good one", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "youre pretty smart", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "tell me a joke", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "whats the meaning of life", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "thats cool", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "interesting", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "you know what I mean", "root_intent": "chitchat", "memory_type": "none", "complexity": "atomic", "entities": {}},

    # ===== CLARIFICATION (only 3) =====
    {"text": "what do you mean", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "can you explain that", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "I dont understand", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "huh", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "what", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "say that again", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "which one do you mean", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "be more specific", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "sorry I didnt get that", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "can you rephrase", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "what did you just say", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},
    {"text": "elaborate please", "root_intent": "clarification", "memory_type": "cwm", "complexity": "atomic", "entities": {}},

    # ===== TASK_STATUS (only 2) =====
    {"text": "what was I doing", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},
    {"text": "what am I working on", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},
    {"text": "whats on my to do list", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},
    {"text": "do I have any pending tasks", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},
    {"text": "what should I be doing right now", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},
    {"text": "show me my active tasks", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},
    {"text": "am I supposed to do something", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},
    {"text": "whats pending", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},
    {"text": "any reminders for me", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},
    {"text": "where was I", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},
    {"text": "what tasks are left", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},
    {"text": "did I finish everything", "root_intent": "task_status", "memory_type": "wm", "complexity": "atomic", "entities": {}},

    # ===== PROFILE_RECALL (only 1) =====
    {"text": "what is my name", "root_intent": "profile_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "name"}},
    {"text": "when is my birthday", "root_intent": "profile_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "birthday"}},
    {"text": "where do I live", "root_intent": "profile_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "address"}},
    {"text": "how old am I", "root_intent": "profile_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "age"}},
    {"text": "what is my email", "root_intent": "profile_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "email"}},
    {"text": "what city am I from", "root_intent": "profile_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "city"}},
    {"text": "do you know my phone number", "root_intent": "profile_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "phone number"}},
    {"text": "whats my last name", "root_intent": "profile_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "last name"}},
    {"text": "what do you know about me", "root_intent": "profile_recall", "memory_type": "sem", "complexity": "atomic", "entities": {}},
    {"text": "have I told you where I work", "root_intent": "profile_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "work"}},

    # ===== CONTACT_RECALL (only 1) =====
    {"text": "who is Bob", "root_intent": "contact_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"name": "Bob"}},
    {"text": "what is alice's phone number", "root_intent": "contact_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"name": "alice", "attribute": "phone number"}},
    {"text": "do you know my coworker john", "root_intent": "contact_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"name": "john", "relationship": "coworker"}},
    {"text": "tell me about sarah", "root_intent": "contact_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"name": "sarah"}},
    {"text": "whats mom's email", "root_intent": "contact_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"name": "mom", "attribute": "email"}},
    {"text": "who is my dentist", "root_intent": "contact_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"attribute": "dentist"}},
    {"text": "show me bob's info", "root_intent": "contact_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"name": "bob"}},
    {"text": "what do you know about dave", "root_intent": "contact_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"name": "dave"}},
    {"text": "who was the friend I mentioned", "root_intent": "contact_recall", "memory_type": "sem", "complexity": "atomic", "entities": {}},
    {"text": "do I know anyone named mike", "root_intent": "contact_recall", "memory_type": "sem", "complexity": "atomic", "entities": {"name": "mike"}},

    # ===== THANKS (only 12, add a few more) =====
    {"text": "thanks a lot", "root_intent": "thanks", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "ty", "root_intent": "thanks", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "much appreciated", "root_intent": "thanks", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "thx", "root_intent": "thanks", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "cheers", "root_intent": "thanks", "memory_type": "none", "complexity": "atomic", "entities": {}},

    # ===== GREETING (only 13, add a few) =====
    {"text": "hi there", "root_intent": "greeting", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "good morning", "root_intent": "greeting", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "sup", "root_intent": "greeting", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "yo", "root_intent": "greeting", "memory_type": "none", "complexity": "atomic", "entities": {}},
    {"text": "hey", "root_intent": "greeting", "memory_type": "none", "complexity": "atomic", "entities": {}},
]


def main():
    """Append augmented data to training file."""
    # Append
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for item in AUGMENTED:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"✅ Appended {len(AUGMENTED)} augmented examples to {OUTPUT_FILE}")
    
    # New totals
    import collections
    data = [json.loads(l) for l in open(OUTPUT_FILE, "r", encoding="utf-8") if l.strip()]
    ic = collections.Counter(d["root_intent"] for d in data)
    print(f"\n📊 New total: {len(data)} examples")
    print(f"\nUpdated distribution:")
    for k, v in ic.most_common():
        status = "✅" if v >= 10 else "⚠️"
        print(f"  {status} {k}: {v}")


if __name__ == "__main__":
    main()
