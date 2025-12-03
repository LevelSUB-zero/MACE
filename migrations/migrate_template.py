import os
import sys
import argparse
import sqlite3

def parse_db_url(url):
    """Parse database URL and extract file path."""
    if url.startswith("sqlite:///"):
        # Remove sqlite:/// prefix
        return url[10:]
    elif url.startswith("sqlite://"):
        # Remove sqlite:// prefix
        return url[9:]
    else:
        # Assume it's already a file path
        return url

def run_migration_sqlite(db_path, sql_file):
    # Parse URL if needed
    db_path = parse_db_url(db_path)
    
    print(f"Running migration {sql_file} on {db_path}...")
    
    with open(sql_file, 'r') as f:
        sql = f.read()
        
    # SQLite compatibility fixes
    # Replace JSONB with TEXT
    sql = sql.replace("JSONB", "TEXT")
    # Replace TIMESTAMPTZ with TEXT
    sql = sql.replace("TIMESTAMPTZ", "TEXT")
    # Replace INSERT OR IGNORE
    sql = sql.replace("IF NOT EXISTS", "IF NOT EXISTS")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executescript(sql)
        conn.commit()
        print("Migration successful.")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mace_stage1.db", help="Database path or URL (e.g., sqlite:///mace_stage1.db)")
    parser.add_argument("--sql", required=True, help="SQL file to run")
    args = parser.parse_args()
    
    run_migration_sqlite(args.db, args.sql)
