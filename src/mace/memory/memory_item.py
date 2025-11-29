from mace.core import idgen, deterministic

class MemoryItem:
    """
    Wrapper for creating schema-compliant MemoryItem objects.
    In Stage-0, we primarily use this for Semantic Memory items if we need to pass them around as objects,
    though SEM is often just KV. This class ensures we can generate the full object if needed.
    """
    def __init__(self, content, memory_type="semantic", canonical_key=None, priority=None):
        self.memory_id = idgen.deterministic_id("memory", str(content))
        self.memory_type = memory_type
        self.canonical_key = canonical_key
        self.content = content # {"text": ..., "structured": ...}
        self.embedding = []
        
        if priority is None:
            self.priority = {
                "recency": 1.0,
                "frequency": 1.0,
                "relevance": 1.0,
                "novelty": 1.0,
                "trust": 1.0
            }
        else:
            self.priority = priority
            
        self.episodic_specific = None
        self.semantic_specific = {
            "version": "1.0",
            "provenance": []
        } if memory_type == "semantic" else None
        
        self.cwm_specific = None
        self.working_specific = None
        
        # Timestamp
        self.created_at = deterministic.deterministic_timestamp(deterministic.increment_counter("memory_time"))

    def to_dict(self):
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type,
            "canonical_key": self.canonical_key,
            "content": self.content,
            "embedding": self.embedding,
            "priority": self.priority,
            "episodic_specific": self.episodic_specific,
            "semantic_specific": self.semantic_specific,
            "cwm_specific": self.cwm_specific,
            "working_specific": self.working_specific,
            "created_at": self.created_at
        }
