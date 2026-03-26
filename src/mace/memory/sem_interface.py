"""
Module: sem_interface
Stage: cross-stage
Purpose: Canonical wrapper for Semantic Memory access. All agents use this interface.

Part of MACE (Meta Aware Cognitive Engine).
"""
from mace.memory import semantic


class SemanticMemoryInterface:
    """Standardized interface for Semantic Memory operations."""

    def __init__(self):
        self.store = semantic.LiveSEMStore()

    def put(self, key: str, value, source: str = "unknown") -> dict:
        """Write a value to Semantic Memory."""
        return semantic.put_sem(key, value, source)

    def get(self, key: str) -> dict:
        """Read a value from Semantic Memory."""
        return semantic.get_sem(key)

    def search(self, query: str, limit: int = 50) -> list:
        """
        Search Semantic Memory by partial key or value match.

        Delegates to the canonical `search_sem` function in semantic.py
        which performs a case-insensitive substring search across keys.

        Args:
            query: Substring to search for.
            limit: Maximum number of results to return.

        Returns:
            List of dicts with 'key', 'value', and 'last_updated'.
        """
        return semantic.search_sem(query, limit)
