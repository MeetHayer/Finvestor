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
# Check if database is connected and if it needs seeding
python3 -c "
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

load_dotenv()
db_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_DSN')
if not db_url:
    print('⚠️  DATABASE_URL not set - skipping database check')
    print('   Make sure PostgreSQL database is linked to this service in Railway')
    sys.exit(2)  # Skip seeding entirely

# Convert to sync psycopg URL
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
elif 'postgresql+asyncpg' in db_url:
    db_url = db_url.replace('postgresql+asyncpg', 'postgresql+psycopg', 1)

try:
    engine = create_engine(db_url, connect_args={'connect_timeout': 5})
    with engine.connect() as conn:
        # Check if ticker table exists
        try:
            result = conn.execute(text('SELECT COUNT(*) FROM ticker LIMIT 1'))
            count = result.scalar()
            if count == 0:
                print('✅ Database connected - empty, will seed from repo data')
                sys.exit(0)  # Need to seed
            else:
                print(f'✅ Database connected - already has {count} tickers, skipping seed')
                sys.exit(1)  # Already seeded
        except Exception as table_err:
            # Table doesn't exist yet (migrations not run)
            print('⚠️  Database connected but ticker table not found - migrations may not have run')
            print(f'   Error: {table_err}')
            sys.exit(0)  # Try to seed anyway
except OperationalError as conn_err:
    error_msg = str(conn_err)
    if 'Name or service not known' in error_msg or 'could not translate host name' in error_msg:
        print('❌ Database connection failed: Cannot resolve database hostname')
        print('   This usually means:')
        print('   1. Database service is not linked to this service in Railway')
        print('   2. DATABASE_URL environment variable is incorrect')
        print('   3. Database service is not running')
        print(f'   Connection string: {db_url[:50]}...')
    else:
        print(f'❌ Database connection failed: {error_msg}')
    sys.exit(2)  # Skip seeding - can't connect
except Exception as e:
    print(f'⚠️  Error checking database: {e}')
    print('   Will attempt seeding anyway...')
    sys.exit(0)  # Try to seed
" 
SEED_EXIT_CODE=$?

if [ $SEED_EXIT_CODE -eq 2 ]; then
    echo "⚠️  Skipping database seeding - connection not available"
    NEEDS_SEED=false
elif [ $SEED_EXIT_CODE -eq 0 ]; then
    NEEDS_SEED=true
else
    NEEDS_SEED=false
fi

if [ "$NEEDS_SEED" = "true" ]; then
    echo "🌱 Seeding database from repo CSV files..."
    # Seed names from nasdaq CSV (non-fatal)
    if [ -f "data/nasdaq_names/nasdaq_screener_nov2024.csv" ]; then
        echo "  → Seeding ticker names..."
        python3 -c "
import sys
from pathlib import Path
from sqlalchemy.exc import OperationalError
sys.path.insert(0, str(Path(__file__).parent))
try:
    from seed.seed_from_kaggle import upsert_names_csv, get_database_url
    from sqlalchemy import create_engine
    db_url = get_database_url()
    engine = create_engine(db_url, connect_args={'connect_timeout': 10})
    count = upsert_names_csv(engine, 'data/nasdaq_names/nasdaq_screener_nov2024.csv')
    print(f'  ✓ Loaded {count} ticker names')
except OperationalError as e:
    error_msg = str(e)
    if 'Name or service not known' in error_msg:
        print('  ❌ Cannot connect to database - make sure it is linked in Railway')
    else:
        print(f'  ❌ Database connection error: {error_msg}')
    sys.exit(0)  # Don't fail deployment
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
from sqlalchemy.exc import OperationalError
sys.path.insert(0, str(Path(__file__).parent))
try:
    from seed.seed_from_kaggle import upsert_prices_dir, get_database_url
    from sqlalchemy import create_engine
    db_url = get_database_url()
    engine = create_engine(db_url, connect_args={'connect_timeout': 10})
    count = upsert_prices_dir(engine, 'data/nyse_prices/archive (1)')
    print(f'  ✓ Loaded price data for {count} symbols')
except OperationalError as e:
    error_msg = str(e)
    if 'Name or service not known' in error_msg:
        print('  ❌ Cannot connect to database - make sure it is linked in Railway')
    else:
        print(f'  ❌ Database connection error: {error_msg}')
    sys.exit(0)  # Don't fail deployment
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

