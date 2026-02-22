"""
Pytest fixtures for stress tests.
"""
import pytest
import os


@pytest.fixture(autouse=True)
def reset_between_tests():
    """Reset state before each test module."""
    # Reset table initialization flags
    try:
        from mace.brainstate import persistence as bs_persistence
        from mace.reflective import writer as reflective_writer
        
        bs_persistence._table_initialized = False
        reflective_writer._table_initialized = False
    except:
        pass
    
    yield
    
    # Cleanup after test
    for db in ["mace_stage1.db", "mace_memory.db"]:
        if os.path.exists(db):
            try:
                os.remove(db)
            except:
                pass
