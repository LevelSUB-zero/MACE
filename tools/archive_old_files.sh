#!/usr/bin/env bash
# Archive Old Files Script
# Safely moves log files older than 90 days to archive directory

set -e

ARCHIVE_DIR="archived/$(date +%Y-%m-%d)"
DAYS_OLD=90

echo "=== Archive Script ==="
echo "Archive directory: $ARCHIVE_DIR"
echo "Moving files older than $DAYS_OLD days"

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

# Find and move old log files
echo "Searching for old files..."
count=0

# Look in logs directory if it exists
if [ -d "logs" ]; then
    while IFS= read -r -d '' file; do
        mv "$file" "$ARCHIVE_DIR/"
        ((count++))
    done < <(find logs -type f -mtime +$DAYS_OLD -print0)
fi

# Look for old DB files
while IFS= read -r -d '' file; do
    mv "$file" "$ARCHIVE_DIR/"
    ((count++))
done < <(find . -maxdepth 1 -name "*.db" -type f -mtime +$DAYS_OLD -print0)

# Create manifest
echo "Creating manifest..."
if [ $count -gt 0 ]; then
    find "$ARCHIVE_DIR" -type f -exec ls -lh {} \; > "$ARCHIVE_DIR/manifest.txt"
    echo "Archived $count files to $ARCHIVE_DIR"
    echo "Manifest: $ARCHIVE_DIR/manifest.txt"
else
    echo "No files to archive"
fi

echo "Done!"
