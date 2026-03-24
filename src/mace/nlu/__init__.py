"""
NLU Module for MACE

Provides hierarchical intent classification with:
- Atomic, conditional, compound, update, meta, and reference_heavy complexity
- Memory routing (wm, cwm, sem, epi, none)
- Schema validation against MemoryAction.json
"""

from .config import ROOT_INTENTS, MEMORY_TYPES, INTENT_TO_MEMORY

__all__ = ["ROOT_INTENTS", "MEMORY_TYPES", "INTENT_TO_MEMORY"]
