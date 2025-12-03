import os
import sqlite3
import json
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

# Global DB config
_DB_URL = os.environ.get("MACE_DB_URL", "sqlite:///mace_stage1.db")

def get_connection():
    """
    Get a database connection based on MACE_DB_URL.
    Supports sqlite:///path and postgresql://...
    """
    if _DB_URL.startswith("sqlite:///"):
        db_path = _DB_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    elif _DB_URL.startswith("postgresql://") or _DB_URL.startswith("postgres://"):
        return psycopg2.connect(_DB_URL, cursor_factory=RealDictCursor)
    else:
        raise ValueError(f"Unsupported DB URL: {_DB_URL}")

def execute_query(conn, query, params=None):
    """
    Execute a query and return cursor.
    Handles parameter substitution differences (SQLite ? vs Postgres %s).
    """
    if params is None:
        params = ()
        
    is_sqlite = isinstance(conn, sqlite3.Connection)
    
    if is_sqlite:
        # SQLite uses ?
        # If params is a dict, it uses :key
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor
    else:
        # Postgres uses %s
        # We need to convert ? to %s if we want a unified query syntax, 
        # or just write queries carefully.
        # For this stage, let's assume we write queries compatible with the driver 
        # or use a simple replacement if needed.
        # Simple hack: replace ? with %s for Postgres
        if "?" in query:
            query = query.replace("?", "%s")
            
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor

def fetch_one(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(row)

def fetch_all(cursor):
    return [dict(row) for row in cursor.fetchall()]
