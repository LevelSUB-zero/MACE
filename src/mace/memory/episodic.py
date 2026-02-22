"""
Episodic Memory - Historical Record

Purpose: Permanent record of past interactions and sessions.
Lifetime: Permanent until consolidated to SEM
Contents: Summaries, payloads, timestamps, job_seed links

Episodic memory stores:
- Individual interactions (request/response pairs)
- Session summaries (from CWM promotion)
- Lineage tracking (which CWM items contributed)
- Knowledge graph entity/relation tags
"""
import datetime
import json
from mace.core import persistence, deterministic, canonical
from mace.config import config_loader
from mace.memory.knowledge_graph import get_knowledge_graph


_table_initialized = False


def _ensure_table_exists():
    """Create episodic table if it doesn't exist."""
    global _table_initialized
    if _table_initialized:
        return
    
    conn = persistence.get_connection()
    try:
        persistence.execute_query(conn, """
            CREATE TABLE IF NOT EXISTS episodic (
                episodic_id TEXT PRIMARY KEY,
                job_seed TEXT,
                summary TEXT,
                payload_json TEXT,
                source_cwm_ids TEXT,
                interaction_type TEXT,
                created_at TEXT
            )
        """)
        # Index for faster lookups
        persistence.execute_query(conn, """
            CREATE INDEX IF NOT EXISTS idx_episodic_job_seed ON episodic(job_seed)
        """)
        persistence.execute_query(conn, """
            CREATE INDEX IF NOT EXISTS idx_episodic_created ON episodic(created_at)
        """)
        conn.commit()
        _table_initialized = True
    finally:
        conn.close()


class EpisodicMemory:
    """
    Episodic Memory - Historical record of interactions.
    
    Stores past interactions for recall and context building.
    """
    
    def __init__(self, job_seed: str = None):
        """
        Initialize Episodic Memory.
        
        Args:
            job_seed: Optional job/session filter (None = all sessions)
        """
        _ensure_table_exists()
        self.job_seed = job_seed
        self._id_counter = 0
    
    def record_interaction(
        self,
        percept_text: str,
        response_text: str,
        agent_id: str,
        job_seed: str = None,
        metadata: dict = None
    ) -> str:
        """
        Record a single interaction (request/response pair).
        
        Args:
            percept_text: The user input
            response_text: The system response
            agent_id: Which agent handled it
            job_seed: Session identifier
            metadata: Additional context (router decision, confidence, etc.)
            
        Returns:
            The episodic_id
        """
        job_seed = job_seed or self.job_seed or "unknown"
        
        # Infer semantic context tags from the interaction
        context_tags = self._infer_context_tags(percept_text, response_text, agent_id)
        
        payload = {
            "percept_text": percept_text,
            "response_text": response_text,
            "agent_id": agent_id,
            "context_tags": context_tags,  # Semantic tags for better recall
            "metadata": metadata or {}
        }
        
        # Create summary with context tag prefix for easier searching
        primary_tag = context_tags[0] if context_tags else "general"
        percept_short = percept_text[:30] if len(percept_text) > 30 else percept_text
        summary = f"[{primary_tag}] {percept_short}"
        
        return self._add_episode(
            summary=summary,
            payload=payload,
            job_seed=job_seed,
            interaction_type="interaction",
            source_cwm_ids=[]
        )
    
    def _infer_context_tags(self, percept_text: str, response_text: str, agent_id: str) -> list:
        """
        Infer semantic context tags from the interaction.
        
        Returns list of tags like:
        - stored_name_context, stored_color_context (for profile storage)
        - recalled_name_context (for profile recall)
        - math_calculation (for math operations)
        - fact_query (for knowledge queries)
        """
        tags = []
        text_lower = percept_text.lower()
        response_lower = response_text.lower()
        
        # Profile/Personal Memory Tags
        if agent_id == "profile_agent":
            # Check what attribute was involved
            attributes = {
                "name": ["name", "called"],
                "color": ["color", "colour"],
                "age": ["age", "old"],
                "job": ["job", "work", "occupation"],
                "birthday": ["birthday", "born"],
                "favorite": ["favorite", "favourite"],
                "location": ["location", "live", "city"]
            }
            
            for attr, keywords in attributes.items():
                if any(kw in text_lower for kw in keywords):
                    # Determine if storing or recalling
                    if "remember" in text_lower or "is" in text_lower:
                        if "stored" in response_lower or "saved" in response_lower:
                            tags.append(f"stored_{attr}_context")
                        else:
                            tags.append(f"attempted_store_{attr}")
                    elif "what" in text_lower or "?" in text_lower:
                        tags.append(f"recalled_{attr}_context")
                    else:
                        tags.append(f"{attr}_context")
            
            # If no specific attribute found
            if not tags:
                if "stored" in response_lower:
                    tags.append("stored_personal_context")
                else:
                    tags.append("personal_context")
        
        # Math Tags
        elif agent_id == "math_agent":
            tags.append("math_calculation")
            if "+" in text_lower:
                tags.append("addition")
            elif "-" in text_lower:
                tags.append("subtraction")
            elif "*" in text_lower or "×" in text_lower:
                tags.append("multiplication")
            elif "/" in text_lower or "÷" in text_lower:
                tags.append("division")
        
        # Knowledge Tags
        elif agent_id == "knowledge_agent":
            tags.append("fact_query")
            if "what is" in text_lower:
                tags.append("definition_query")
            elif "who is" in text_lower:
                tags.append("person_query")
            elif "when" in text_lower:
                tags.append("time_query")
            elif "where" in text_lower:
                tags.append("location_query")
        
        # Generic/Fallback
        else:
            tags.append("general_context")
        
        # Also extract dynamic knowledge graph tags
        try:
            kg = get_knowledge_graph()
            kg_tags = kg.generate_context_tags(percept_text)
            tags.extend(kg_tags)
        except Exception:
            pass  # KG extraction failure shouldn't break tagging
        
        return tags if tags else ["untagged"]
    
    def search_by_context(self, context_tag: str, limit: int = 10) -> list:
        """
        Search episodes by context tag.
        
        Args:
            context_tag: The tag to search for (e.g., "stored_name_context")
            limit: Maximum results
        """
        conn = persistence.get_connection()
        try:
            # Search in both summary (has [tag]) and payload (has context_tags)
            cur = persistence.execute_query(
                conn,
                """SELECT * FROM episodic 
                   WHERE summary LIKE ? OR payload_json LIKE ? 
                   ORDER BY created_at DESC LIMIT ?""",
                (f"%[{context_tag}]%", f'%"{context_tag}"%', limit)
            )
            rows = persistence.fetch_all(cur)
            return [self._row_to_episode(row) for row in rows]
        finally:
            conn.close()
    
    def record_session_end(self, cwm_items: list, job_seed: str = None) -> str:
        """
        Record the end of a session by consolidating CWM items.
        
        Args:
            cwm_items: List of CWM items to consolidate
            job_seed: Session identifier
            
        Returns:
            The episodic_id
        """
        job_seed = job_seed or self.job_seed or "unknown"
        
        # Extract CWM IDs
        cwm_ids = [item.get("item_id", "") for item in cwm_items]
        
        # Create summary
        item_count = len(cwm_items)
        summary = f"Session end: {item_count} context items consolidated"
        
        # Create payload with all CWM content
        payload = {
            "session_summary": True,
            "item_count": item_count,
            "items": [
                {
                    "item_id": item.get("item_id"),
                    "content": item.get("content"),
                    "source_wm_id": item.get("source_wm_id")
                }
                for item in cwm_items
            ]
        }
        
        return self._add_episode(
            summary=summary,
            payload=payload,
            job_seed=job_seed,
            interaction_type="session_end",
            source_cwm_ids=cwm_ids
        )
    
    def _add_episode(
        self,
        summary: str,
        payload: dict,
        job_seed: str,
        interaction_type: str,
        source_cwm_ids: list
    ) -> str:
        """Internal: Add an episode to the database."""
        self._id_counter += 1
        
        # Generate deterministic ID
        id_payload = f"{job_seed}:episodic:{self._id_counter}:{canonical.canonical_json_serialize(payload)}"
        episodic_id = deterministic.deterministic_id("episodic", id_payload)
        
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        conn = persistence.get_connection()
        try:
            persistence.execute_query(conn, """
                INSERT OR REPLACE INTO episodic 
                (episodic_id, job_seed, summary, payload_json, source_cwm_ids, interaction_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                episodic_id,
                job_seed,
                summary,
                canonical.canonical_json_serialize(payload),
                json.dumps(source_cwm_ids),
                interaction_type,
                timestamp
            ))
            conn.commit()
            return episodic_id
        finally:
            conn.close()
    
    def get(self, episodic_id: str) -> dict:
        """Get a specific episode by ID."""
        conn = persistence.get_connection()
        try:
            cur = persistence.execute_query(
                conn,
                "SELECT * FROM episodic WHERE episodic_id = ?",
                (episodic_id,)
            )
            row = persistence.fetch_one(cur)
            if row:
                return self._row_to_episode(row)
            return None
        finally:
            conn.close()
    
    def get_recent(self, n: int = 10, job_seed: str = None) -> list:
        """
        Get the N most recent episodes.
        
        Args:
            n: Number of episodes to retrieve
            job_seed: Optional filter by session
        """
        conn = persistence.get_connection()
        try:
            if job_seed:
                cur = persistence.execute_query(
                    conn,
                    "SELECT * FROM episodic WHERE job_seed = ? ORDER BY created_at DESC LIMIT ?",
                    (job_seed, n)
                )
            else:
                cur = persistence.execute_query(
                    conn,
                    "SELECT * FROM episodic ORDER BY created_at DESC LIMIT ?",
                    (n,)
                )
            rows = persistence.fetch_all(cur)
            return [self._row_to_episode(row) for row in rows]
        finally:
            conn.close()
    
    def search_by_summary(self, query: str, limit: int = 10) -> list:
        """
        Search episodes by summary text (basic LIKE search).
        
        Args:
            query: Text to search for
            limit: Maximum results
        """
        conn = persistence.get_connection()
        try:
            cur = persistence.execute_query(
                conn,
                "SELECT * FROM episodic WHERE summary LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit)
            )
            rows = persistence.fetch_all(cur)
            return [self._row_to_episode(row) for row in rows]
        finally:
            conn.close()
    
    def search_content(self, query: str, limit: int = 10) -> list:
        """
        Full-text search across summary AND payload content.
        
        This searches both the summary and the raw payload JSON,
        enabling recall by any word in the interaction.
        
        Args:
            query: Text to search for (case-insensitive)
            limit: Maximum results
        """
        conn = persistence.get_connection()
        try:
            cur = persistence.execute_query(
                conn,
                """SELECT * FROM episodic 
                   WHERE summary LIKE ? OR payload_json LIKE ? 
                   ORDER BY created_at DESC LIMIT ?""",
                (f"%{query}%", f"%{query}%", limit)
            )
            rows = persistence.fetch_all(cur)
            return [self._row_to_episode(row) for row in rows]
        finally:
            conn.close()
    
    def search_by_keywords(self, keywords: list, match_all: bool = False, limit: int = 10) -> list:
        """
        Search by multiple keywords.
        
        Args:
            keywords: List of keywords to search for
            match_all: If True, all keywords must match. If False, any keyword matches.
            limit: Maximum results
        """
        if not keywords:
            return []
        
        conn = persistence.get_connection()
        try:
            # Build query conditions
            conditions = []
            params = []
            for kw in keywords:
                conditions.append("(summary LIKE ? OR payload_json LIKE ?)")
                params.extend([f"%{kw}%", f"%{kw}%"])
            
            operator = " AND " if match_all else " OR "
            where_clause = operator.join(conditions)
            
            cur = persistence.execute_query(
                conn,
                f"SELECT * FROM episodic WHERE {where_clause} ORDER BY created_at DESC LIMIT ?",
                params + [limit]
            )
            rows = persistence.fetch_all(cur)
            return [self._row_to_episode(row) for row in rows]
        finally:
            conn.close()
    
    def get_session_history(self, job_seed: str) -> list:
        """Get all episodes for a specific session."""
        conn = persistence.get_connection()
        try:
            cur = persistence.execute_query(
                conn,
                "SELECT * FROM episodic WHERE job_seed = ? ORDER BY created_at ASC",
                (job_seed,)
            )
            rows = persistence.fetch_all(cur)
            return [self._row_to_episode(row) for row in rows]
        finally:
            conn.close()
    
    def _row_to_episode(self, row: dict) -> dict:
        """Convert DB row to episode dict."""
        return {
            "episodic_id": row["episodic_id"],
            "job_seed": row["job_seed"],
            "summary": row["summary"],
            "payload": json.loads(row["payload_json"]),
            "source_cwm_ids": json.loads(row["source_cwm_ids"]) if row["source_cwm_ids"] else [],
            "interaction_type": row.get("interaction_type", "unknown"),
            "created_at": row["created_at"]
        }
    
    def __repr__(self):
        return f"EpisodicMemory(job_seed={self.job_seed})"
