import pytest
import os
import time

@pytest.fixture(autouse=True)
def db_cleanup():
    """
    Fixture to clean up the database and journal after each test.
    """
    yield
    # Teardown
    # Retry loop for Windows file locking
    for _ in range(5):
        try:
            if os.path.exists("mace_memory.db"):
                os.remove("mace_memory.db")
            if os.path.exists("logs/sem_write_journal.jsonl"):
                os.remove("logs/sem_write_journal.jsonl")
            break
        except PermissionError:
            time.sleep(0.1)
