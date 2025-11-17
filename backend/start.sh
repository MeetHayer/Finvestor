#!/bin/bash
set -e

echo "🔄 Running database migrations..."
cd /app/backend
alembic upgrade head

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
    # Seed names from nasdaq CSV
    if [ -f "data/nasdaq_names/nasdaq_screener_nov2024.csv" ]; then
        echo "  → Seeding ticker names..."
        python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from seed.seed_from_kaggle import upsert_names_csv, get_database_url
from sqlalchemy import create_engine
engine = create_engine(get_database_url())
count = upsert_names_csv(engine, 'data/nasdaq_names/nasdaq_screener_nov2024.csv')
print(f'  ✓ Loaded {count} ticker names')
"
    fi
    
    # Seed prices from NYSE CSV files
    if [ -d "data/nyse_prices/archive (1)" ]; then
        echo "  → Seeding price data (this may take a few minutes)..."
        python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from seed.seed_from_kaggle import upsert_prices_dir, get_database_url
from sqlalchemy import create_engine
engine = create_engine(get_database_url())
count = upsert_prices_dir(engine, 'data/nyse_prices/archive (1)')
print(f'  ✓ Loaded price data for {count} symbols')
"
    fi
    echo "✅ Database seeding complete!"
else
    echo "✅ Database already seeded, skipping."
fi

echo "🚀 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

