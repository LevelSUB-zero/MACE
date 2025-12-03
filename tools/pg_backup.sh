#!/bin/bash
# Backup script for MACE Stage-1 Postgres DB
# Usage: ./pg_backup.sh <db_url> <output_dir>

DB_URL=$1
OUTPUT_DIR=$2
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if [ -z "$DB_URL" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: $0 <db_url> <output_dir>"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
FILENAME="$OUTPUT_DIR/mace_backup_$TIMESTAMP.sql"

echo "Backing up to $FILENAME..."
pg_dump "$DB_URL" -F p -f "$FILENAME"

if [ $? -eq 0 ]; then
    echo "Backup successful."
else
    echo "Backup failed."
    exit 1
fi
