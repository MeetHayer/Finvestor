#!/bin/bash
# Import database dump to Railway PostgreSQL
# Usage: ./import_to_railway.sh <RAILWAY_DATABASE_URL>

set -e

if [ -z "$1" ]; then
    echo "❌ Error: Railway DATABASE_URL required"
    echo ""
    echo "Usage: ./import_to_railway.sh <RAILWAY_DATABASE_URL>"
    echo ""
    echo "To get your Railway DATABASE_URL:"
    echo "  1. Go to Railway dashboard"
    echo "  2. Open your PostgreSQL service"
    echo "  3. Go to Variables tab"
    echo "  4. Copy the DATABASE_URL value"
    echo ""
    echo "Example:"
    echo "  ./import_to_railway.sh \"postgresql://postgres:password@host.railway.app:5432/railway\""
    exit 1
fi

RAILWAY_URL="$1"

# Check if using internal Railway URL (won't work from your Mac)
if [[ "$RAILWAY_URL" == *".railway.internal"* ]]; then
    echo "❌ Error: You're using Railway's INTERNAL URL (postgres.railway.internal)"
    echo ""
    echo "This URL only works from within Railway's network, not from your Mac."
    echo ""
    echo "🔧 To get the PUBLIC URL:"
    echo "  1. Go to Railway dashboard"
    echo "  2. Open your PostgreSQL service"
    echo "  3. Go to 'Connect' or 'Networking' tab"
    echo "  4. Look for 'Public Networking' or 'Connection String'"
    echo "  5. Copy the URL (should be yamabiko.proxy.rlwy.net or similar, NOT .railway.internal)"
    echo ""
    exit 1
fi

# Get script directory (works from anywhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prefer essential_data.dump if it exists, otherwise fallback to full dump
if [ -f "$SCRIPT_DIR/essential_data.dump" ]; then
    DUMP_FILE="$SCRIPT_DIR/essential_data.dump"
else
    DUMP_FILE="$SCRIPT_DIR/db_export.dump"
fi

if [ ! -f "$DUMP_FILE" ]; then
    echo "❌ Error: Dump file not found: $DUMP_FILE"
    echo "   Run export_to_railway.sh first to create the dump"
    exit 1
fi

echo "📥 Importing to Railway PostgreSQL..."
echo "   URL: ${RAILWAY_URL:0:50}..."

# Wait for database to be ready (Railway PostgreSQL can take 1-2 minutes to initialize)
echo "⏳ Checking if database is ready..."
MAX_RETRIES=12
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if PGCONNECT_TIMEOUT=5 psql "$RAILWAY_URL" -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ Database is ready!"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "   Database not ready yet, waiting 10 seconds... (attempt $RETRY_COUNT/$MAX_RETRIES)"
            sleep 10
        else
            echo "❌ Database still not ready after $MAX_RETRIES attempts"
            echo "   Please wait a few minutes and try again, or check Railway dashboard"
            exit 1
        fi
    fi
done

# Import using pg_restore with options for large dumps
echo "📦 Starting import (this may take several minutes for large databases)..."
PGCONNECT_TIMEOUT=0 pg_restore \
  -d "$RAILWAY_URL" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --verbose \
  --single-transaction \
  "$DUMP_FILE"

echo ""
echo "✅ Import complete!"
echo "   Your Railway database now has all your local data!"

