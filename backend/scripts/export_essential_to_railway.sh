#!/bin/bash
# Export only essential tables (no giant price history) and import to Railway later
# Usage: ./export_essential_to_railway.sh

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUMP_FILE="$SCRIPT_DIR/essential_data.dump"

echo "📤 Exporting essential tables from local PostgreSQL..."

LOCAL_DB="${LOCAL_DB:-postgresql://finvestor:finvestor1234@localhost:5432/sampleStocksData}"

pg_dump "$LOCAL_DB" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --format=custom \
  --file="$DUMP_FILE" \
  --table=ticker \
  --table=portfolio \
  --table=portfolio_holding \
  --table=portfolio_transaction \
  --table=portfolio_cash_ledger \
  --table=watchlist \
  --table=watchlist_tickers \
  --table=fundamentals_cache

echo "✅ Essential export complete: $DUMP_FILE"
echo ""
echo "Next steps:"
echo "  1. Delete and recreate PostgreSQL service in Railway (fresh DB)"
echo "  2. Run ./import_to_railway.sh \"YOUR_RAILWAY_DATABASE_URL\""
echo ""

