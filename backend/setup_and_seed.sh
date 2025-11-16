#!/bin/bash
# Setup and seed script for Finvestor backend

echo "🚀 Starting Finvestor Backend Setup..."

# Create and activate virtual environment
echo "📦 Setting up virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Update pip
echo "⬆️  Updating pip..."
pip install -U pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] psycopg[binary] yfinance fredapi python-dotenv alembic httpx pandas numpy pydantic loguru tenacity asyncpg greenlet

# Initialize Alembic (if not already initialized)
echo "🗄️  Initializing database migrations..."
alembic revision --autogenerate -m "init schema"
alembic upgrade head

# Run seeding script
echo "🌱 Seeding database..."
python seed/seed_data.py

echo "✅ Setup complete!"
echo ""
echo "To verify the data, connect to PostgreSQL and run:"
echo "SELECT symbol, COUNT(*) FROM price_daily pd JOIN ticker t ON pd.ticker_id=t.id GROUP BY symbol ORDER BY 2 DESC;"











