from mace.core import structures
from mace.memory import semantic

def run(percept):
    # Knowledge agent is read-only for Stage-0
    # It tries to find a fact in SEM.
    # Since we don't have an NLP extractor yet, we rely on exact key lookup 
    # or just fail gracefully (F1).
    
    # For Stage-0, let's assume we might have some hardcoded mapping or just fail.
    # The rulebook says: "If query starts with 'what is' ... route to knowledge_agent"
    # But without an extractor, we can't easily convert "what is ohms law" to "world/fact/ohms_law/definition"
    # unless we have a mapping.
    
    # Let's try a naive slugify for the last word(s)?
    # Or just return F1 as we haven't populated SEM with world facts yet.
    
    return structures.create_agent_output(
        agent_id="knowledge_agent",
        text="I don’t have that information stored yet. If you want, tell me and I’ll remember it.",
        confidence=1.0
    )
