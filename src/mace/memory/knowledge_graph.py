"""
Knowledge Graph Memory - Dynamic Entity-Relationship Tagging

This module provides a graph-based memory structure where:
- Nodes = Entities (people, places, things)
- Edges = Relationships and attributes
- Tags are dynamically created based on content

Examples:
  "my friend's name is John" → entity:john, relation:friend_of_user
  "John is a footballer"     → entity:john, attribute:occupation=footballer
  "John's favorite color"    → entity:john, attribute:favorite_color=red
"""
import json
import datetime
import re
from mace.core import persistence, deterministic, canonical


_table_initialized = False


def _ensure_table_exists():
    """Create knowledge graph tables if they don't exist."""
    global _table_initialized
    if _table_initialized:
        return
    
    conn = persistence.get_connection()
    try:
        # Entities table (nodes)
        persistence.execute_query(conn, """
            CREATE TABLE IF NOT EXISTS kg_entities (
                entity_id TEXT PRIMARY KEY,
                name TEXT,
                entity_type TEXT,
                attributes_json TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Relations table (edges)
        persistence.execute_query(conn, """
            CREATE TABLE IF NOT EXISTS kg_relations (
                relation_id TEXT PRIMARY KEY,
                source_entity_id TEXT,
                target_entity_id TEXT,
                relation_type TEXT,
                metadata_json TEXT,
                created_at TEXT,
                FOREIGN KEY (source_entity_id) REFERENCES kg_entities(entity_id),
                FOREIGN KEY (target_entity_id) REFERENCES kg_entities(entity_id)
            )
        """)
        
        # Indexes for fast lookups
        persistence.execute_query(conn, """
            CREATE INDEX IF NOT EXISTS idx_entities_name ON kg_entities(name)
        """)
        persistence.execute_query(conn, """
            CREATE INDEX IF NOT EXISTS idx_relations_source ON kg_relations(source_entity_id)
        """)
        
        conn.commit()
        _table_initialized = True
    finally:
        conn.close()


class KnowledgeGraph:
    """
    Dynamic Knowledge Graph for semantic memory.
    
    Stores entities and their relationships, allowing:
    - Dynamic entity creation on first mention
    - Attribute accumulation over time
    - Relationship tracking between entities
    """
    
    def __init__(self):
        _ensure_table_exists()
        self._user_entity_id = self._get_or_create_entity("user", "person")
    
    def _get_or_create_entity(self, name: str, entity_type: str = "unknown") -> str:
        """Get existing entity or create new one."""
        name_lower = name.lower().strip()
        
        conn = persistence.get_connection()
        try:
            # Check if exists
            cur = persistence.execute_query(
                conn,
                "SELECT entity_id FROM kg_entities WHERE LOWER(name) = ?",
                (name_lower,)
            )
            row = persistence.fetch_one(cur)
            
            if row:
                return row["entity_id"]
            
            # Create new entity
            entity_id = deterministic.deterministic_id("kg_entity", f"{name_lower}:{entity_type}")
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            persistence.execute_query(conn, """
                INSERT INTO kg_entities (entity_id, name, entity_type, attributes_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (entity_id, name_lower, entity_type, "{}", timestamp, timestamp))
            conn.commit()
            
            return entity_id
        finally:
            conn.close()
    
    def add_attribute(self, entity_name: str, attribute: str, value: str) -> dict:
        """
        Add an attribute to an entity.
        
        Example: add_attribute("john", "occupation", "footballer")
        Creates: john:occupation=footballer
        """
        entity_id = self._get_or_create_entity(entity_name, "person")
        
        conn = persistence.get_connection()
        try:
            # Get current attributes
            cur = persistence.execute_query(
                conn,
                "SELECT attributes_json FROM kg_entities WHERE entity_id = ?",
                (entity_id,)
            )
            row = persistence.fetch_one(cur)
            attrs = json.loads(row["attributes_json"]) if row else {}
            
            # Add/update attribute
            attrs[attribute] = value
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            persistence.execute_query(conn, """
                UPDATE kg_entities SET attributes_json = ?, updated_at = ? WHERE entity_id = ?
            """, (json.dumps(attrs), timestamp, entity_id))
            conn.commit()
            
            return {
                "entity": entity_name,
                "attribute": attribute,
                "value": value,
                "tag": f"{entity_name}:{attribute}={value}"
            }
        finally:
            conn.close()
    
    def add_relation(self, source_name: str, relation_type: str, target_name: str) -> dict:
        """
        Add a relationship between entities.
        
        Example: add_relation("john", "friend_of", "user")
        Creates: john --friend_of--> user
        """
        source_id = self._get_or_create_entity(source_name)
        target_id = self._get_or_create_entity(target_name)
        
        relation_id = deterministic.deterministic_id(
            "kg_relation", 
            f"{source_id}:{relation_type}:{target_id}"
        )
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        conn = persistence.get_connection()
        try:
            persistence.execute_query(conn, """
                INSERT OR REPLACE INTO kg_relations 
                (relation_id, source_entity_id, target_entity_id, relation_type, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (relation_id, source_id, target_id, relation_type, "{}", timestamp))
            conn.commit()
            
            return {
                "source": source_name,
                "relation": relation_type,
                "target": target_name,
                "tag": f"{source_name}:{relation_type}:{target_name}"
            }
        finally:
            conn.close()
    
    def get_entity(self, name: str) -> dict:
        """Get entity with all its attributes."""
        conn = persistence.get_connection()
        try:
            cur = persistence.execute_query(
                conn,
                "SELECT * FROM kg_entities WHERE LOWER(name) = ?",
                (name.lower(),)
            )
            row = persistence.fetch_one(cur)
            
            if not row:
                return None
            
            return {
                "entity_id": row["entity_id"],
                "name": row["name"],
                "type": row["entity_type"],
                "attributes": json.loads(row["attributes_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
        finally:
            conn.close()
    
    def get_relations(self, entity_name: str) -> list:
        """Get all relations for an entity."""
        entity = self.get_entity(entity_name)
        if not entity:
            return []
        
        entity_id = entity["entity_id"]
        
        conn = persistence.get_connection()
        try:
            # Get outgoing relations
            cur = persistence.execute_query(conn, """
                SELECT r.*, e.name as target_name 
                FROM kg_relations r 
                JOIN kg_entities e ON r.target_entity_id = e.entity_id
                WHERE r.source_entity_id = ?
            """, (entity_id,))
            outgoing = persistence.fetch_all(cur)
            
            # Get incoming relations
            cur = persistence.execute_query(conn, """
                SELECT r.*, e.name as source_name 
                FROM kg_relations r 
                JOIN kg_entities e ON r.source_entity_id = e.entity_id
                WHERE r.target_entity_id = ?
            """, (entity_id,))
            incoming = persistence.fetch_all(cur)
            
            relations = []
            for r in outgoing:
                relations.append({
                    "direction": "outgoing",
                    "relation": r["relation_type"],
                    "target": r["target_name"]
                })
            for r in incoming:
                relations.append({
                    "direction": "incoming",
                    "relation": r["relation_type"],
                    "source": r["source_name"]
                })
            
            return relations
        finally:
            conn.close()
    
    def parse_and_store(self, text: str) -> list:
        """
        Parse natural language and extract entities/relations.
        
        Examples:
        - "my friend's name is John" → john:relation=friend_of_user
        - "John is a footballer" → john:occupation=footballer
        - "John's favorite color is red" → john:favorite_color=red
        """
        text_lower = text.lower()
        stored = []
        
        # Pattern: "my <relation>'s name is <name>"
        # e.g., "my friend's name is John"
        match = re.search(r"my (\w+)(?:'s)? name is (\w+)", text_lower)
        if match:
            relation = match.group(1)  # friend, brother, etc.
            name = match.group(2)       # john
            stored.append(self.add_relation(name, f"{relation}_of", "user"))
            stored.append(self.add_attribute(name, "name", name))
        
        # Pattern: "<name> is a/an <occupation>"
        # e.g., "John is a footballer"
        match = re.search(r"(\w+) is (?:a|an) (\w+)", text_lower)
        if match:
            name = match.group(1)
            occupation = match.group(2)
            stored.append(self.add_attribute(name, "occupation", occupation))
        
        # Pattern: "<name>'s <attribute> is <value>"
        # e.g., "John's favorite color is red"
        match = re.search(r"(\w+)(?:'s)? (\w+(?:\s+\w+)?) is (\w+)", text_lower)
        if match:
            name = match.group(1)
            attr = match.group(2).replace(" ", "_")
            value = match.group(3)
            if name not in ["my", "what", "who", "this", "that"]:
                stored.append(self.add_attribute(name, attr, value))
        
        # Pattern: "remember my <attribute> is <value>"
        # e.g., "remember my name is Alice"
        match = re.search(r"(?:remember )?my (\w+) is (\w+)", text_lower)
        if match:
            attr = match.group(1)
            value = match.group(2)
            stored.append(self.add_attribute("user", attr, value))
        
        return stored
    
    def generate_context_tags(self, text: str) -> list:
        """
        Generate dynamic context tags from text.
        
        Returns tags like:
        - stored:john:friend_of:user
        - stored:john:occupation=footballer
        - stored:user:name=alice
        """
        stored = self.parse_and_store(text)
        return [item["tag"] for item in stored]
    
    def recall_about(self, entity_name: str) -> dict:
        """
        Recall everything known about an entity.
        
        Returns all attributes and relationships.
        """
        entity = self.get_entity(entity_name)
        if not entity:
            return {"found": False, "entity": entity_name}
        
        relations = self.get_relations(entity_name)
        
        return {
            "found": True,
            "entity": entity_name,
            "type": entity["type"],
            "attributes": entity["attributes"],
            "relations": relations
        }


# Singleton instance
_kg_instance = None


def get_knowledge_graph() -> KnowledgeGraph:
    """Get the singleton KnowledgeGraph instance."""
    global _kg_instance
    if _kg_instance is None:
        _kg_instance = KnowledgeGraph()
    return _kg_instance
