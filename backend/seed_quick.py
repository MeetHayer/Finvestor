"""
Quick seed script using yfinance - REAL DATA, NO API KEYS NEEDED
Seeds a few popular tickers for testing
"""
import asyncio
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import Ticker, PriceDaily

# Symbols to seed
SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'JNJ']

async def seed_ticker(session, symbol: str):
    """Seed a single ticker with real data from yfinance (history only, no info to avoid rate limits)"""
    try:
        print(f"📈 Fetching {symbol}...")
        
        # Get ticker - only use history(), skip .info to avoid rate limits
        ticker = yf.Ticker(symbol)
        
        # Get historical data (1 year) - this doesn't require API calls to info endpoint
        hist = ticker.history(period="1y", timeout=30)
        
        if hist is None or len(hist) == 0:
            print(f"  ⚠️  No data for {symbol}")
            return False
        
        print(f"  ✓ Got {len(hist)} days of data")
        
        # Insert ticker with minimal info (avoid calling .info)
        ticker_stmt = pg_insert(Ticker).values(
            symbol=symbol,
            name=symbol,  # We'll update name later if needed
            exchange='UNKNOWN'
        ).on_conflict_do_update(
            index_elements=['symbol'],
            set_=dict(exchange='UNKNOWN')
        ).returning(Ticker.id)
        
        result = await session.execute(ticker_stmt)
        ticker_id = result.scalar_one()
        await session.commit()
        
        # Prepare price data
        price_rows = []
        for date, row in hist.iterrows():
            date_val = date.date() if hasattr(date, 'date') else pd.to_datetime(date).date()
            price_rows.append({
                'ticker_id': ticker_id,
                'date': date_val,
                'open': float(row['Open']) if pd.notna(row['Open']) else None,
                'high': float(row['High']) if pd.notna(row['High']) else None,
                'low': float(row['Low']) if pd.notna(row['Low']) else None,
                'close': float(row['Close']) if pd.notna(row['Close']) else None,
                'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
                'pe': None,  # Skip for now to avoid rate limits
                'market_cap': None,  # Skip for now to avoid rate limits
            })
        
        # Bulk insert prices
        if price_rows:
            price_stmt = pg_insert(PriceDaily).values(price_rows)
            price_stmt = price_stmt.on_conflict_do_nothing()
            await session.execute(price_stmt)
            await session.commit()
            print(f"  ✓ Inserted {len(price_rows)} price records")
            return True
        
        return False
        
    except Exception as e:
        print(f"  ❌ Error with {symbol}: {str(e)[:100]}")
        await session.rollback()
        return False

async def main():
    """Seed database with real data"""
    print("🚀 Starting quick seed with yfinance...")
    print(f"📊 Seeding {len(SYMBOLS)} symbols: {', '.join(SYMBOLS)}")
    
    async with SessionLocal() as session:
        success_count = 0
        for symbol in SYMBOLS:
            if await seed_ticker(session, symbol):
                success_count += 1
            # Longer delay to avoid rate limits
            await asyncio.sleep(2)
        
        print(f"\n✅ Seed complete! {success_count}/{len(SYMBOLS)} symbols seeded successfully")

if __name__ == "__main__":
    asyncio.run(main())

