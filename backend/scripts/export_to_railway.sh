#!/bin/bash
# Export from local PostgreSQL and import to Railway
# Usage: ./export_to_railway.sh

set -e

# Get script directory (works from anywhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUMP_FILE="$SCRIPT_DIR/db_export.dump"

echo "📤 Exporting from local PostgreSQL..."

# Local database connection (adjust these to match your local setup)
LOCAL_DB="${LOCAL_DB:-postgresql://finvestor:finvestor1234@localhost:5432/sampleStocksData}"

# Export schema and data
pg_dump "$LOCAL_DB" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --format=custom \
  --file="$DUMP_FILE"

echo "✅ Export complete: $DUMP_FILE"
echo ""
echo "📥 To import to Railway:"
echo "   1. Get your Railway DATABASE_URL from Railway dashboard"
echo "   2. Run: ./import_to_railway.sh \"YOUR_RAILWAY_DATABASE_URL\""
echo ""
echo "   Or manually:"
echo "   pg_restore -d \"YOUR_RAILWAY_URL\" --clean --if-exists --no-owner --no-acl $DUMP_FILE"

