"""
Quick seed with sample data - manual insert to get frontend working
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
import uuid

from app.db import SessionLocal
from app.models import Ticker, PriceDaily

# Sample data for a few tickers
SAMPLE_DATA = {
    'AAPL': {'name': 'Apple Inc.', 'exchange': 'NASDAQ'},
    'MSFT': {'name': 'Microsoft Corporation', 'exchange': 'NASDAQ'},
    'GOOGL': {'name': 'Alphabet Inc.', 'exchange': 'NASDAQ'},
}

async def seed_sample():
    """Insert sample price data"""
    print("🚀 Seeding sample data...")
    
    async with SessionLocal() as session:
        for symbol, info in SAMPLE_DATA.items():
            print(f"📈 Seeding {symbol}...")
            
            # Insert/update ticker
            ticker_stmt = pg_insert(Ticker).values(
                symbol=symbol,
                name=info['name'],
                exchange=info['exchange']
            ).on_conflict_do_update(
                index_elements=['symbol'],
                set_=dict(name=info['name'], exchange=info['exchange'])
            ).returning(Ticker.id)
            
            result = await session.execute(ticker_stmt)
            ticker_id = result.scalar_one()
            await session.commit()
            
            # Generate 30 days of sample price data (last 30 days)
            price_rows = []
            base_price = {'AAPL': 180.0, 'MSFT': 420.0, 'GOOGL': 140.0}[symbol]
            
            for i in range(30):
                date = (datetime.now() - timedelta(days=30-i)).date()
                # Simple price movement simulation
                variation = (i % 10 - 5) * 2  # Oscillating pattern
                close = base_price + variation + (i * 0.5)  # Slight upward trend
                
                price_rows.append({
                    'ticker_id': ticker_id,
                    'date': date,
                    'open': close - 1.0,
                    'high': close + 1.5,
                    'low': close - 2.0,
                    'close': close,
                    'volume': 10000000 + (i * 100000),
                    'pe': 25.0 + i * 0.1,
                    'market_cap': int(base_price * 15000000000),  # Simulated market cap
                })
            
            # Insert prices
            price_stmt = pg_insert(PriceDaily).values(price_rows)
            price_stmt = price_stmt.on_conflict_do_nothing()
            await session.execute(price_stmt)
            await session.commit()
            
            print(f"  ✓ Inserted {len(price_rows)} price records for {symbol}")
        
        print("\n✅ Sample data seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_sample())


