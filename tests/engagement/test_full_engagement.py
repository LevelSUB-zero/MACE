"""
MACE Full System Engagement Test v2

Simulates diverse human-like interaction for 3 minutes, testing:
- Router (math, profile, knowledge, generic)
- Memory hierarchy (WM, CWM, Episodic)
- Knowledge Graph (entity-relationship tagging)
- Stage 3 (governance, containment, advisory)
- Error handling and recovery

Run: python tests/engagement/test_full_engagement.py
"""
import os
import sys
import time
import random
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from mace.core import deterministic
from mace.runtime import executor
from mace.memory.episodic import EpisodicMemory
from mace.memory.knowledge_graph import get_knowledge_graph


# Test duration (30 seconds for debug)
TEST_DURATION_SECONDS = 30

# Diverse prompt generators
def gen_math():
    """Generate random math problems."""
    a = random.randint(1, 100)
    b = random.randint(1, 100)
    ops = [
        (f"what is {a} + {b}", a + b),
        (f"{a} plus {b}", a + b),
        (f"calculate {a} * {b}", a * b),
        (f"{a} times {b}", a * b),
        (f"what's {a} minus {b}", a - b),
        (f"{a} - {b}", a - b),
        (f"{a} divided by {max(1, b)}", a // max(1, b)),
    ]
    return random.choice(ops)[0]

# User profile data
NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
COLORS = ["blue", "red", "green", "purple", "orange", "yellow"]
CITIES = ["Tokyo", "Paris", "London", "New York", "Berlin", "Sydney"]
JOBS = ["engineer", "teacher", "doctor", "artist", "chef", "writer"]
FOODS = ["pizza", "sushi", "pasta", "tacos", "ramen", "curry"]
HOBBIES = ["coding", "reading", "gaming", "hiking", "cooking", "music"]

def gen_profile_store():
    """Generate profile storage commands."""
    patterns = [
        f"my name is {random.choice(NAMES)}",
        f"remember my favorite color is {random.choice(COLORS)}",
        f"my city is {random.choice(CITIES)}",
        f"my job is {random.choice(JOBS)}",
        f"my favorite food is {random.choice(FOODS)}",
        f"my hobby is {random.choice(HOBBIES)}",
        f"my age is {random.randint(18, 80)}",
    ]
    return random.choice(patterns)

def gen_profile_recall():
    """Generate profile recall commands."""
    attrs = ["name", "favorite color", "city", "job", "favorite food", "hobby", "age"]
    return f"what is my {random.choice(attrs)}"

# Contact data
CONTACT_NAMES = ["Bob", "Sarah", "Mike", "Emma", "Jack", "Lisa"]
ROLES = ["teacher", "footballer", "doctor", "chef", "engineer", "artist"]

def gen_contact_store():
    """Generate contact storage commands."""
    name = random.choice(CONTACT_NAMES)
    patterns = [
        f"my friend's name is {name}",
        f"{name} is a {random.choice(ROLES)}",
        f"{name}'s favorite color is {random.choice(COLORS)}",
        f"remember {name} is my {random.choice(['friend', 'colleague', 'neighbor'])}",
    ]
    return random.choice(patterns)

def gen_contact_recall():
    """Generate contact recall commands."""
    name = random.choice(CONTACT_NAMES)
    return f"who is {name}"

def gen_knowledge_teach():
    """Generate knowledge teaching commands."""
    facts = [
        ("the capital of France", "Paris"),
        ("photosynthesis", "the process plants use to convert sunlight to energy"),
        ("pi", "approximately 3.14159"),
        ("gravity", "the force that attracts objects to each other"),
        ("Python", "a programming language"),
    ]
    fact = random.choice(facts)
    return f"remember that {fact[0]} is {fact[1]}"

def gen_knowledge_query():
    """Generate knowledge queries."""
    queries = [
        "what is the capital of France",
        "what is photosynthesis",
        "what is pi",
        "what is gravity",
        "what is Python",
    ]
    return random.choice(queries)

def gen_conversation():
    """Generate conversational prompts."""
    prompts = [
        "hello",
        "hi there",
        "how are you",
        "tell me a joke",
        "what can you do",
        "help me",
        "thanks",
        "thank you",
        "good morning",
        "that's cool",
    ]
    return random.choice(prompts)

def gen_edge():
    """Generate edge case inputs."""
    return random.choice([
        "",
        "   ",
        "!@#$%",
        "a" * 50,
        "SELECT * FROM users",
        "DROP TABLE",
        "<script>alert(1)</script>",
    ])


# Category generators with weights
GENERATORS = [
    ("math", gen_math, 20),
    ("profile_store", gen_profile_store, 18),
    ("profile_recall", gen_profile_recall, 15),
    ("contact_store", gen_contact_store, 12),
    ("contact_recall", gen_contact_recall, 8),
    ("knowledge_teach", gen_knowledge_teach, 10),
    ("knowledge_query", gen_knowledge_query, 8),
    ("conversation", gen_conversation, 6),
    ("edge_case", gen_edge, 3),
]


class EngagementTestRunner:
    """Runs continuous engagement test with metrics."""
    
    def __init__(self, duration_seconds: int = TEST_DURATION_SECONDS):
        self.duration = duration_seconds
        self.start_time = None
        
        # Metrics
        self.total = 0
        self.success = 0
        self.failed = 0
        self.categories = {}
        self.times = []
        self.responses = []
        
    def _clean_state(self):
        """Clean database state."""
        for db in ["mace_stage1.db", "mace_memory.db", "stage3.db"]:
            if os.path.exists(db):
                os.remove(db)
        
        # Reset modules
        from mace.memory import cwm, episodic, knowledge_graph
        from mace.brainstate import persistence as bs_persistence
        from mace.reflective import writer as reflective_writer
        
        cwm._table_initialized = False
        episodic._table_initialized = False
        knowledge_graph._table_initialized = False
        bs_persistence._table_initialized = False
        reflective_writer._table_initialized = False
        
    def _select_prompt(self) -> tuple:
        """Select weighted random prompt."""
        total_w = sum(g[2] for g in GENERATORS)
        r = random.uniform(0, total_w)
        
        cumulative = 0
        for name, gen_fn, weight in GENERATORS:
            cumulative += weight
            if r <= cumulative:
                return name, gen_fn()
        
        return GENERATORS[0][0], GENERATORS[0][1]()
    
    def run(self):
        """Run the test."""
        print("=" * 70)
        print("MACE FULL SYSTEM ENGAGEMENT TEST v2")
        print(f"Duration: {self.duration}s | Diverse prompts | Live metrics")
        print("=" * 70)
        
        self._clean_state()
        deterministic.init_seed(f"test_{datetime.now().isoformat()}")
        
        self.start_time = time.time()
        end_time = self.start_time + self.duration
        
        print(f"\nStarted: {datetime.now().strftime('%H:%M:%S')}\n")
        
        while time.time() < end_time:
            cat, prompt = self._select_prompt()
            
            start = time.time()
            try:
                result, _ = executor.execute(prompt)
                ok = True
                resp = result.get("text", "")[:40]
            except Exception as e:
                ok = False
                resp = str(e)[:40]
            elapsed = time.time() - start
            
            # Track
            self.total += 1
            self.categories[cat] = self.categories.get(cat, 0) + 1
            self.times.append(elapsed)
            if ok:
                self.success += 1
            else:
                self.failed += 1
            
            # Display
            remaining = end_time - time.time()
            status = "✓" if ok else "✗"
            print(f"[{remaining:5.0f}s] {status} {cat:16} | {prompt[:25]:25} → {resp}")
            
            self.responses.append((cat, prompt, resp, ok))
            
            # Human-like delay
            time.sleep(random.uniform(0.3, 1.5))
        
        self._summary()
    
    def _summary(self):
        """Print summary."""
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        print(f"\nRequests: {self.total} | Success: {self.success} ({100*self.success/max(1,self.total):.0f}%) | Failed: {self.failed}")
        
        if self.times:
            print(f"Response: avg={sum(self.times)/len(self.times)*1000:.0f}ms, min={min(self.times)*1000:.0f}ms, max={max(self.times)*1000:.0f}ms")
        
        print("\nBy Category:")
        for cat, count in sorted(self.categories.items(), key=lambda x: -x[1]):
            print(f"  {cat:18}: {count:3}")
        
        # Check memory
        print("\nMemory:")
        try:
            ep = EpisodicMemory()
            print(f"  Episodes: {len(ep.get_recent(200))}")
            kg = get_knowledge_graph()
            user = kg.recall_about("user")
            if user.get("found"):
                print(f"  User attrs: {len(user.get('attributes', {}))}")
        except:
            pass
        
        # Sample responses
        print("\nSample Responses:")
        samples = random.sample(self.responses, min(5, len(self.responses)))
        for cat, prompt, resp, ok in samples:
            print(f"  [{cat}] {prompt[:30]} → {resp}")


if __name__ == "__main__":
    EngagementTestRunner(TEST_DURATION_SECONDS).run()
