#!/bin/bash
# Restore script for MACE Stage-1 Postgres DB
# Usage: ./pg_restore.sh <db_url> <backup_file>

DB_URL=$1
BACKUP_FILE=$2

if [ -z "$DB_URL" ] || [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <db_url> <backup_file>"
    exit 1
fi

echo "Restoring from $BACKUP_FILE to $DB_URL..."
# Transactional restore
psql "$DB_URL" -f "$BACKUP_FILE" --single-transaction

if [ $? -eq 0 ]; then
    echo "Restore successful."
else
    echo "Restore failed."
    exit 1
fi
