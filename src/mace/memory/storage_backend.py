import sqlite3
import os
import json

class StorageBackend:
    def __init__(self, db_path="mace_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """
        Initialize the SQLite database with deterministic settings.
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, timeout=10.0)
        
        # Enforce deterministic behavior
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA journal_mode=DELETE")
        
        # Create table if not exists
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sem_kv (
                canonical_key TEXT PRIMARY KEY,
                value TEXT,
                last_updated TEXT
            )
        """)
        self.conn.commit()

    def put(self, key, value, timestamp):
        """
        Write a key-value pair to the database.
        value is expected to be a JSON string.
        """
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO sem_kv (canonical_key, value, last_updated)
                VALUES (?, ?, ?)
            """, (key, value, timestamp))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            # Log error? For now just return False as per spec F5
            return False

    def get(self, key):
        """
        Retrieve a value by key.
        Returns (value, last_updated) or (None, None) if not found.
        """
        cursor = self.conn.execute("""
            SELECT value, last_updated FROM sem_kv WHERE canonical_key = ?
        """, (key,))
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
        return None, None

    def close(self):
        self.conn.close()
