"""
Working Memory (WM) - Live Request Context

Purpose: Short-term memory for the current request/tick.
Capacity: 7 items (configurable via wm_capacity)
TTL: 10 ticks (configurable via wm_ttl_ticks)
Eviction: FIFO when full, TTL expiry promotes to CWM
"""
import datetime
from mace.core import deterministic, canonical
from mace.config import config_loader


class WorkingMemory:
    """
    Working Memory for live request context.
    
    Items have TTL and are promoted to CWM when they expire.
    """
    
    def __init__(self, job_seed: str, on_expire_callback=None):
        """
        Initialize WM for a specific job.
        
        Args:
            job_seed: Job identifier for deterministic ID generation
            on_expire_callback: Function(item) called when items expire (for CWM promotion)
        """
        self.job_seed = job_seed
        self.items = []
        self.max_capacity = config_loader.get_wm_capacity()
        self.default_ttl = config_loader.get_wm_ttl()
        self.on_expire_callback = on_expire_callback
        self._item_counter = 0
    
    def add(self, content: dict, memory_id: str = None, ttl: int = None) -> str:
        """
        Add an item to Working Memory.
        
        Args:
            content: The content to store (dict)
            memory_id: Optional explicit ID (will be generated if not provided)
            ttl: Optional TTL override (uses default if not provided)
            
        Returns:
            The memory_id of the added item
        """
        # Generate deterministic ID if not provided
        if memory_id is None:
            self._item_counter += 1
            id_payload = f"{self.job_seed}:wm:{self._item_counter}:{canonical.canonical_json_serialize(content)}"
            memory_id = deterministic.deterministic_id("wm_item", id_payload)
        
        # Use default TTL if not specified
        if ttl is None:
            ttl = self.default_ttl
        
        # Evict oldest if at capacity
        while len(self.items) >= self.max_capacity:
            evicted = self.items.pop(0)
            if self.on_expire_callback:
                self.on_expire_callback(evicted)
        
        # Create item
        item = {
            "memory_id": memory_id,
            "content": content,
            "ttl": ttl,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "job_seed": self.job_seed
        }
        
        self.items.append(item)
        return memory_id
    
    def get(self, memory_id: str) -> dict:
        """Get a specific item by ID."""
        for item in self.items:
            if item["memory_id"] == memory_id:
                return item
        return None
    
    def get_all(self) -> list:
        """Get all active items."""
        return self.items.copy()
    
    def get_active(self) -> list:
        """Get items with TTL > 0."""
        return [item for item in self.items if item["ttl"] > 0]
    
    def tick(self) -> list:
        """
        Advance one tick: decrement TTLs, expire items.
        
        Returns:
            List of expired items (already promoted via callback)
        """
        expired = []
        active = []
        
        for item in self.items:
            item["ttl"] -= 1
            if item["ttl"] <= 0:
                expired.append(item)
                if self.on_expire_callback:
                    self.on_expire_callback(item)
            else:
                active.append(item)
        
        self.items = active
        return expired
    
    def clear(self):
        """Clear all items (with expiry callbacks)."""
        for item in self.items:
            if self.on_expire_callback:
                self.on_expire_callback(item)
        self.items = []
    
    def __len__(self):
        return len(self.items)
    
    def __repr__(self):
        return f"WorkingMemory(items={len(self.items)}, capacity={self.max_capacity})"
