"""
Seed database using pandas-datareader for historical stock data
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
import pandas as pd
import pandas_datareader.data as web

from app.db import SessionLocal
from app.models import Ticker, PriceDaily

# Symbols to seed
SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'JNJ']

# Stock name mappings
STOCK_NAMES = {
    'AAPL': 'Apple Inc.',
    'MSFT': 'Microsoft Corporation',
    'GOOGL': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.',
    'TSLA': 'Tesla Inc.',
    'META': 'Meta Platforms Inc.',
    'NVDA': 'NVIDIA Corporation',
    'JPM': 'JPMorgan Chase & Co.',
    'V': 'Visa Inc.',
    'JNJ': 'Johnson & Johnson',
}

async def seed_ticker(session, symbol: str):
    """Seed a single ticker using pandas-datareader"""
    try:
        print(f"📈 Fetching {symbol}...")
        
        # Get date range (1 year)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Fetch data using pandas-datareader (Yahoo Finance)
        try:
            df = web.DataReader(symbol, 'yahoo', start_date, end_date)
        except Exception as e:
            print(f"  ⚠️  Failed to fetch {symbol}: {e}")
            return False
        
        if df is None or len(df) == 0:
            print(f"  ⚠️  No data for {symbol}")
            return False
        
        print(f"  ✓ Got {len(df)} days of data")
        
        # Insert ticker
        ticker_stmt = pg_insert(Ticker).values(
            symbol=symbol,
            name=STOCK_NAMES.get(symbol, symbol),
            exchange='UNKNOWN'
        ).on_conflict_do_update(
            index_elements=['symbol'],
            set_=dict(name=STOCK_NAMES.get(symbol, symbol))
        ).returning(Ticker.id)
        
        result = await session.execute(ticker_stmt)
        ticker_id = result.scalar_one()
        await session.commit()
        
        # Prepare price data from DataFrame
        price_rows = []
        for date, row in df.iterrows():
            date_val = date.date() if hasattr(date, 'date') else pd.to_datetime(date).date()
            
            price_rows.append({
                'ticker_id': ticker_id,
                'date': date_val,
                'open': float(row['Open']) if pd.notna(row['Open']) else None,
                'high': float(row['High']) if pd.notna(row['High']) else None,
                'low': float(row['Low']) if pd.notna(row['Low']) else None,
                'close': float(row['Close']) if pd.notna(row['Close']) else None,
                'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
                'pe': None,  # Not available from datareader
                'market_cap': None,  # Not available from datareader
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
    """Seed database with real data from pandas-datareader"""
    print("🚀 Starting seed with pandas-datareader...")
    print(f"📊 Seeding {len(SYMBOLS)} symbols: {', '.join(SYMBOLS)}")
    print("")
    
    async with SessionLocal() as session:
        success_count = 0
        for idx, symbol in enumerate(SYMBOLS, 1):
            print(f"[{idx}/{len(SYMBOLS)}] ", end="")
            if await seed_ticker(session, symbol):
                success_count += 1
            # Delay to avoid rate limits
            await asyncio.sleep(1)
        
        print(f"\n✅ Seed complete! {success_count}/{len(SYMBOLS)} symbols seeded successfully")
        print(f"📊 Total records: Check database with: SELECT COUNT(*) FROM price_daily;")

if __name__ == "__main__":
    asyncio.run(main())


