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

echo "📊 Checking database connection and seeding status..."
# Check if database is connected and if it needs seeding - WITH RETRIES
python3 -c "
import os
import sys
import time
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

load_dotenv()
db_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_DSN')
if not db_url:
    print('⚠️  DATABASE_URL not set - will retry connection check')
    print('   Waiting for Railway to inject DATABASE_URL...')
    # Wait and retry - Railway might inject it during startup
    for attempt in range(5):
        time.sleep(3)
        db_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_DSN')
        if db_url:
            print(f'✅ DATABASE_URL found after {attempt + 1} attempts')
            break
    if not db_url:
        print('❌ DATABASE_URL still not set after retries')
        print('   Make sure PostgreSQL database is linked to this service in Railway')
        sys.exit(0)  # Still try to seed - maybe it will work

# Convert to sync psycopg URL
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
elif 'postgresql+asyncpg' in db_url:
    db_url = db_url.replace('postgresql+asyncpg', 'postgresql+psycopg', 1)

# RETRY CONNECTION - database might not be ready immediately
max_retries = 10
for attempt in range(max_retries):
    try:
        engine = create_engine(db_url, connect_args={'connect_timeout': 10})
        with engine.connect() as conn:
            # Check if ticker table exists
            try:
                result = conn.execute(text('SELECT COUNT(*) FROM ticker LIMIT 1'))
                count = result.scalar()
                if count == 0:
                    print(f'✅ Database connected (attempt {attempt + 1}) - empty, will seed from repo data')
                    sys.exit(0)  # Need to seed
                else:
                    print(f'✅ Database connected (attempt {attempt + 1}) - already has {count} tickers, skipping seed')
                    sys.exit(1)  # Already seeded
            except Exception as table_err:
                # Table doesn't exist yet (migrations not run) - that's OK, we'll seed
                print(f'✅ Database connected (attempt {attempt + 1}) - tables not ready yet, will seed')
                sys.exit(0)  # Try to seed anyway
    except OperationalError as conn_err:
        error_msg = str(conn_err)
        if attempt < max_retries - 1:
            wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
            print(f'⏳ Database connection attempt {attempt + 1}/{max_retries} failed, retrying in {wait_time}s...')
            if 'Name or service not known' in error_msg:
                print('   (Database may not be linked yet - Railway might still be setting up)')
            time.sleep(wait_time)
        else:
            # Last attempt failed
            if 'Name or service not known' in error_msg or 'could not translate host name' in error_msg:
                print('❌ Database connection failed after all retries: Cannot resolve database hostname')
                print('   This usually means database service is not linked to this service in Railway')
                print('   BUT - will still attempt seeding in case connection works during seeding')
            else:
                print(f'❌ Database connection failed after all retries: {error_msg}')
            sys.exit(0)  # STILL TRY TO SEED - maybe connection will work during seeding
    except Exception as e:
        print(f'⚠️  Error checking database (attempt {attempt + 1}): {e}')
        if attempt < max_retries - 1:
            time.sleep(2)
        else:
            print('   Will attempt seeding anyway...')
            sys.exit(0)  # Try to seed
" 
SEED_EXIT_CODE=$?

if [ $SEED_EXIT_CODE -eq 0 ]; then
    NEEDS_SEED=true
else
    NEEDS_SEED=false
fi

if [ "$NEEDS_SEED" = "true" ]; then
    echo "🌱 FORCING DATABASE SEEDING - will retry until it works..."
    # Seed names from nasdaq CSV - WITH RETRIES
    if [ -f "data/nasdaq_names/nasdaq_screener_nov2024.csv" ]; then
        echo "  → Seeding ticker names (with retries)..."
        python3 -c "
import sys
import time
from pathlib import Path
from sqlalchemy.exc import OperationalError
sys.path.insert(0, str(Path(__file__).parent))

max_retries = 15
for attempt in range(max_retries):
    try:
        from seed.seed_from_kaggle import upsert_names_csv, get_database_url
        from sqlalchemy import create_engine
        db_url = get_database_url()
        engine = create_engine(db_url, connect_args={'connect_timeout': 15})
        count = upsert_names_csv(engine, 'data/nasdaq_names/nasdaq_screener_nov2024.csv')
        print(f'  ✅ SUCCESS! Loaded {count} ticker names')
        sys.exit(0)
    except OperationalError as e:
        error_msg = str(e)
        if attempt < max_retries - 1:
            wait_time = min(2 ** attempt, 15)
            print(f'  ⏳ Seeding attempt {attempt + 1}/{max_retries} failed, retrying in {wait_time}s...')
            if 'Name or service not known' in error_msg:
                print('     (Database may not be linked yet - waiting for Railway...)')
            time.sleep(wait_time)
        else:
            print(f'  ❌ Seeding names failed after {max_retries} attempts: {error_msg}')
            print('     Will continue anyway - server will start')
            sys.exit(0)
    except Exception as e:
        if attempt < max_retries - 1:
            print(f'  ⏳ Seeding attempt {attempt + 1}/{max_retries} failed: {e}, retrying...')
            time.sleep(3)
        else:
            print(f'  ⚠️  Seeding names failed after {max_retries} attempts: {e}')
            sys.exit(0)
" || echo "  ⚠️  Seeding names had issues but continuing..."
    fi
    
    # Seed prices from NYSE CSV files - WITH RETRIES
    if [ -d "data/nyse_prices/archive (1)" ]; then
        echo "  → Seeding price data (this may take a few minutes, with retries)..."
        python3 -c "
import sys
import time
from pathlib import Path
from sqlalchemy.exc import OperationalError
sys.path.insert(0, str(Path(__file__).parent))

max_retries = 15
for attempt in range(max_retries):
    try:
        from seed.seed_from_kaggle import upsert_prices_dir, get_database_url
        from sqlalchemy import create_engine
        db_url = get_database_url()
        engine = create_engine(db_url, connect_args={'connect_timeout': 15})
        count = upsert_prices_dir(engine, 'data/nyse_prices/archive (1)')
        print(f'  ✅ SUCCESS! Loaded price data for {count} symbols')
        sys.exit(0)
    except OperationalError as e:
        error_msg = str(e)
        if attempt < max_retries - 1:
            wait_time = min(2 ** attempt, 15)
            print(f'  ⏳ Seeding attempt {attempt + 1}/{max_retries} failed, retrying in {wait_time}s...')
            if 'Name or service not known' in error_msg:
                print('     (Database may not be linked yet - waiting for Railway...)')
            time.sleep(wait_time)
        else:
            print(f'  ❌ Seeding prices failed after {max_retries} attempts: {error_msg}')
            print('     Will continue anyway - server will start')
            sys.exit(0)
    except Exception as e:
        if attempt < max_retries - 1:
            print(f'  ⏳ Seeding attempt {attempt + 1}/{max_retries} failed: {e}, retrying...')
            time.sleep(3)
        else:
            print(f'  ⚠️  Seeding prices failed after {max_retries} attempts: {e}')
            sys.exit(0)
" || echo "  ⚠️  Seeding prices had issues but continuing..."
    fi
    echo "✅ Database seeding complete (or will retry on next deploy if connection wasn't ready)"
else
    echo "✅ Database already seeded, skipping."
fi

echo "🚀 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

