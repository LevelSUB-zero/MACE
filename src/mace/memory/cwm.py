"""
Contextual Working Memory (CWM) - Session Context

Purpose: Maintain context across multiple requests in a session.
Capacity: 20 items (configurable via max_cwm_items)
Lifetime: Persists for session/job duration, DB-backed
Eviction: Oldest items when full, promotes to Episodic on session end
"""
import datetime
import json
from mace.core import persistence, deterministic, canonical
from mace.config import config_loader


_table_initialized = False


def _ensure_table_exists():
    """Create cwm_items table if it doesn't exist."""
    global _table_initialized
    if _table_initialized:
        return
    
    conn = persistence.get_connection()
    try:
        persistence.execute_query(conn, """
            CREATE TABLE IF NOT EXISTS cwm_items (
                item_id TEXT PRIMARY KEY,
                job_seed TEXT,
                content_json TEXT,
                source_wm_id TEXT,
                priority REAL DEFAULT 1.0,
                created_at TEXT,
                expires_at TEXT
            )
        """)
        conn.commit()
        _table_initialized = True
    finally:
        conn.close()


class ContextualWorkingMemory:
    """
    Contextual Working Memory - Session-level context.
    
    Persists across multiple requests within the same job/session.
    DB-backed for durability.
    """
    
    def __init__(self, job_seed: str, on_session_end_callback=None):
        """
        Initialize CWM for a specific job/session.
        
        Args:
            job_seed: Session/job identifier
            on_session_end_callback: Function(items) called on session end (for Episodic)
        """
        _ensure_table_exists()
        self.job_seed = job_seed
        self.max_capacity = config_loader.get_limits().get('max_cwm_items', 20)
        self.on_session_end_callback = on_session_end_callback
        self._item_counter = 0
        self._items_cache = None  # Lazy load
    
    def _load_items(self) -> list:
        """Load items from DB for this job_seed."""
        if self._items_cache is not None:
            return self._items_cache
        
        conn = persistence.get_connection()
        try:
            cur = persistence.execute_query(
                conn,
                "SELECT item_id, content_json, source_wm_id, priority, created_at FROM cwm_items WHERE job_seed = ? ORDER BY created_at ASC",
                (self.job_seed,)
            )
            rows = persistence.fetch_all(cur)
            self._items_cache = []
            for row in rows:
                self._items_cache.append({
                    "item_id": row["item_id"],
                    "content": json.loads(row["content_json"]),
                    "source_wm_id": row["source_wm_id"],
                    "priority": row["priority"],
                    "created_at": row["created_at"],
                    "job_seed": self.job_seed
                })
            return self._items_cache
        finally:
            conn.close()
    
    def add(self, content: dict, source_wm_id: str = None, priority: float = 1.0) -> str:
        """
        Add an item to CWM.
        
        Args:
            content: The content to store
            source_wm_id: ID of the WM item this came from (for lineage)
            priority: Priority score (higher = more important)
            
        Returns:
            The item_id
        """
        items = self._load_items()
        
        # Evict oldest if at capacity
        while len(items) >= self.max_capacity:
            evicted = items.pop(0)
            self._delete_from_db(evicted["item_id"])
        
        # Generate deterministic ID
        self._item_counter += 1
        id_payload = f"{self.job_seed}:cwm:{self._item_counter}:{canonical.canonical_json_serialize(content)}"
        item_id = deterministic.deterministic_id("cwm_item", id_payload)
        
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        item = {
            "item_id": item_id,
            "content": content,
            "source_wm_id": source_wm_id,
            "priority": priority,
            "created_at": timestamp,
            "job_seed": self.job_seed
        }
        
        # Persist to DB
        self._save_to_db(item)
        
        # Update cache
        items.append(item)
        self._items_cache = items
        
        return item_id
    
    def add_from_wm(self, wm_item: dict) -> str:
        """
        Promote a WM item to CWM.
        
        Args:
            wm_item: The expired WM item to promote
            
        Returns:
            The new CWM item_id
        """
        return self.add(
            content=wm_item["content"],
            source_wm_id=wm_item["memory_id"],
            priority=1.0
        )
    
    def get(self, item_id: str) -> dict:
        """Get a specific item by ID."""
        items = self._load_items()
        for item in items:
            if item["item_id"] == item_id:
                return item
        return None
    
    def get_all(self) -> list:
        """Get all items for this session."""
        return self._load_items().copy()
    
    def get_recent(self, n: int = 5) -> list:
        """Get the N most recent items."""
        items = self._load_items()
        return items[-n:] if len(items) >= n else items.copy()
    
    def end_session(self) -> list:
        """
        End the session: promote all items to Episodic and clear.
        
        Returns:
            List of all promoted items
        """
        items = self._load_items()
        
        if self.on_session_end_callback and items:
            self.on_session_end_callback(items)
        
        # Clear from DB
        self._clear_from_db()
        self._items_cache = []
        
        return items
    
    def _save_to_db(self, item: dict):
        """Persist item to database."""
        conn = persistence.get_connection()
        try:
            persistence.execute_query(conn, """
                INSERT OR REPLACE INTO cwm_items 
                (item_id, job_seed, content_json, source_wm_id, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                item["item_id"],
                self.job_seed,
                canonical.canonical_json_serialize(item["content"]),
                item.get("source_wm_id"),
                item.get("priority", 1.0),
                item["created_at"]
            ))
            conn.commit()
        finally:
            conn.close()
    
    def _delete_from_db(self, item_id: str):
        """Delete item from database."""
        conn = persistence.get_connection()
        try:
            persistence.execute_query(conn, 
                "DELETE FROM cwm_items WHERE item_id = ?", 
                (item_id,)
            )
            conn.commit()
        finally:
            conn.close()
    
    def _clear_from_db(self):
        """Clear all items for this job_seed."""
        conn = persistence.get_connection()
        try:
            persistence.execute_query(conn,
                "DELETE FROM cwm_items WHERE job_seed = ?",
                (self.job_seed,)
            )
            conn.commit()
        finally:
            conn.close()
    
    def __len__(self):
        return len(self._load_items())
    
    def __repr__(self):
        return f"ContextualWorkingMemory(job_seed={self.job_seed}, items={len(self)})"
