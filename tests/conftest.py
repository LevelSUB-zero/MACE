import pytest
import os
import time

@pytest.fixture(autouse=True)
def db_cleanup():
    """
    Fixture to clean up the database and journal after each test, AND reset module init flags 
    so subsequent tests correctly recreate the database tables.
    """
    # Teardown & Setup - always clear before starting a test
    for db_file in ["mace_memory.db", "mace_stage1.db", "mace.db", "lr01_training.db"]:
        for _ in range(5):
            try:
                if os.path.exists(db_file):
                    os.remove(db_file)
                break
            except PermissionError:
                time.sleep(0.1)
                
    for log_file in ["logs/sem_write_journal.jsonl", "logs/reflective_log.jsonl"]:
        for _ in range(5):
            try:
                if os.path.exists(log_file):
                    os.remove(log_file)
                break
            except PermissionError:
                time.sleep(0.1)
                
    # Reset internal flags across the suite
    try:
        from mace.reflective import writer
        from mace.brainstate import persistence as bs_persistence
        from mace.memory import semantic
        import mace.memory.episodic as eps
        import mace.memory.cwm as cwm_module
        
        writer._table_initialized = False
        bs_persistence._table_initialized = False
        semantic._tables_initialized = False
        eps._table_initialized = False
        cwm_module._table_initialized = False
    except ImportError:
        pass
        
    yield
    
    # Also clean up after test finishes (some tests might not tearDown cleanly if exceptions happen)
    for db_file in ["mace_memory.db", "mace_stage1.db", "mace.db", "lr01_training.db"]:
        for _ in range(5):
            try:
                if os.path.exists(db_file):
                    os.remove(db_file)
                break
            except PermissionError:
                time.sleep(0.1)
