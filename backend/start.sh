#!/bin/bash
# Don't use set -e - we want to handle errors gracefully

cd /app/backend

# Check if DATABASE_URL is set (warn but don't exit - let app handle it)
if [ -z "$DATABASE_URL" ] && [ -z "$POSTGRES_DSN" ]; then
    echo "⚠️  WARNING: DATABASE_URL not set!"
    echo "   In Railway: Add a PostgreSQL database service and link it to this service."
    echo "   Railway will automatically provide DATABASE_URL environment variable."
    echo "   Continuing anyway - app will show error on startup..."
fi

echo "🔄 Running database migrations..."
alembic upgrade head || {
    echo "⚠️  Migration failed - database may not be connected yet"
    echo "   Continuing anyway - migrations will retry on next deploy"
}

echo "📊 Checking if database needs seeding..."
# Check if ticker table has any data
python3 -c "
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
db_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_DSN')
if not db_url:
    exit(1)

# Convert to sync psycopg URL
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
elif 'postgresql+asyncpg' in db_url:
    db_url = db_url.replace('postgresql+asyncpg', 'postgresql+psycopg', 1)

engine = create_engine(db_url)
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM ticker LIMIT 1'))
        count = result.scalar()
        if count == 0:
            print('Database is empty, seeding from repo data...')
            exit(0)  # Need to seed
        else:
            print(f'Database already has {count} tickers, skipping seed.')
            exit(1)  # Already seeded
except Exception as e:
    print(f'Error checking database: {e}')
    exit(0)  # Assume needs seeding if error
" || NEEDS_SEED=true

if [ "$NEEDS_SEED" = "true" ]; then
    echo "🌱 Seeding database from repo CSV files..."
    # Seed names from nasdaq CSV (non-fatal)
    if [ -f "data/nasdaq_names/nasdaq_screener_nov2024.csv" ]; then
        echo "  → Seeding ticker names..."
        python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
try:
    from seed.seed_from_kaggle import upsert_names_csv, get_database_url
    from sqlalchemy import create_engine
    engine = create_engine(get_database_url())
    count = upsert_names_csv(engine, 'data/nasdaq_names/nasdaq_screener_nov2024.csv')
    print(f'  ✓ Loaded {count} ticker names')
except Exception as e:
    print(f'  ⚠️  Seeding names failed: {e}')
    sys.exit(0)  # Don't fail deployment
" || echo "  ⚠️  Seeding names skipped"
    fi
    
    # Seed prices from NYSE CSV files (non-fatal)
    if [ -d "data/nyse_prices/archive (1)" ]; then
        echo "  → Seeding price data (this may take a few minutes)..."
        python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
try:
    from seed.seed_from_kaggle import upsert_prices_dir, get_database_url
    from sqlalchemy import create_engine
    engine = create_engine(get_database_url())
    count = upsert_prices_dir(engine, 'data/nyse_prices/archive (1)')
    print(f'  ✓ Loaded price data for {count} symbols')
except Exception as e:
    print(f'  ⚠️  Seeding prices failed: {e}')
    sys.exit(0)  # Don't fail deployment
" || echo "  ⚠️  Seeding prices skipped"
    fi
    echo "✅ Database seeding attempt complete!"
else
    echo "✅ Database already seeded, skipping."
fi

echo "🚀 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

