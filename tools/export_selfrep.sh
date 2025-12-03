#!/bin/bash
# Export SelfRepresentation data to JSONL
# Usage: ./export_selfrep.sh <db_url> <output_file>

DB_URL=$1
OUTPUT_FILE=$2

if [ -z "$DB_URL" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <db_url> <output_file>"
    exit 1
fi

echo "Exporting SelfRepresentation nodes to $OUTPUT_FILE..."
psql "$DB_URL" -c "COPY (SELECT row_to_json(t) FROM (SELECT * FROM self_representation_nodes) t) TO STDOUT" > "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo "Export successful."
else
    echo "Export failed."
    exit 1
fi
