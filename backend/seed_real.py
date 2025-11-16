"""
Seed database with REAL data using existing market data services
Uses Finnhub → AlphaVantage → YahooQuery fallback
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db import SessionLocal
from app.models import Ticker, PriceDaily
from app.services.data_sources import StockDataFetcher

# Symbols to seed (start with a few to test)
SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']

async def insert_ticker(session, symbol: str, name: str, exchange: str):
    """Insert or update ticker"""
    stmt = pg_insert(Ticker).values(
        symbol=symbol,
        name=name,
        exchange=exchange
    ).on_conflict_do_update(
        index_elements=['symbol'],
        set_=dict(name=name, exchange=exchange)
    ).returning(Ticker.id)
    
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()

async def insert_price_data(session, ticker_id, history_df, pe=None, market_cap=None, avg_volume=None):
    """Insert price data"""
    import pandas as pd
    
    price_rows = []
    for date_idx, row in history_df.iterrows():
        # Handle date index
        if hasattr(date_idx, 'date'):
            date_val = date_idx.date()
        else:
            date_val = pd.to_datetime(date_idx).date()
        
        # Normalize column names
        open_val = row.get('Open', row.get('open'))
        high_val = row.get('High', row.get('high'))
        low_val = row.get('Low', row.get('low'))
        close_val = row.get('Close', row.get('close'))
        volume_val = row.get('Volume', row.get('volume'))
        
        price_rows.append({
            'ticker_id': ticker_id,
            'date': date_val,
            'open': float(open_val) if pd.notna(open_val) else None,
            'high': float(high_val) if pd.notna(high_val) else None,
            'low': float(low_val) if pd.notna(low_val) else None,
            'close': float(close_val) if pd.notna(close_val) else None,
            'volume': int(volume_val) if pd.notna(volume_val) else 0,
            'pe': float(pe) if pe else None,
            'market_cap': int(market_cap) if market_cap else None,
        })
    
    if price_rows:
        stmt = pg_insert(PriceDaily).values(price_rows)
        stmt = stmt.on_conflict_do_nothing()
        await session.execute(stmt)
        await session.commit()
    
    return len(price_rows)

async def seed_ticker(session, symbol: str, fetcher: StockDataFetcher):
    """Seed a single ticker using real data sources"""
    try:
        print(f"📈 Fetching REAL data for {symbol}...")
        
        # Fetch data using the existing service (Finnhub → AlphaVantage → YahooQuery)
        data, has_partial = await fetcher.fetch_stock_data(symbol)
        
        if data is None:
            print(f"  ❌ FAILED: No data from any source for {symbol}")
            return False
        
        print(f"  ✓ Got data from {data['source']}")
        
        # Insert ticker
        ticker_id = await insert_ticker(
            session,
            data['symbol'],
            data['name'],
            data['exchange']
        )
        
        # Insert price data
        rows_inserted = await insert_price_data(
            session,
            ticker_id,
            data['history'],
            data['pe'],
            data['market_cap'],
            data['avg_volume']
        )
        
        print(f"  ✓ Inserted {rows_inserted} price records")
        return True
        
    except Exception as e:
        print(f"  ❌ Error with {symbol}: {str(e)[:150]}")
        await session.rollback()
        return False

async def main():
    """Seed database with REAL data"""
    print("🚀 Seeding REAL data using API keys...")
    print(f"📊 Symbols: {', '.join(SYMBOLS)}")
    print("")
    
    fetcher = StockDataFetcher()
    
    async with SessionLocal() as session:
        success_count = 0
        for idx, symbol in enumerate(SYMBOLS, 1):
            print(f"[{idx}/{len(SYMBOLS)}] ", end="")
            if await seed_ticker(session, symbol, fetcher):
                success_count += 1
            # Delay to respect rate limits
            await asyncio.sleep(2)
        
        print(f"\n✅ Seed complete! {success_count}/{len(SYMBOLS)} symbols seeded successfully")
        
        if success_count == 0:
            print("\n⚠️  ISSUE: All data sources failed.")
            print("   Possible reasons:")
            print("   1. API keys invalid or expired")
            print("   2. Rate limits exceeded")
            print("   3. Network/connectivity issues")
            print("   4. Yahoo Finance blocking requests")
            print("\n   Check .env file for:")
            print("   - FINNHUB_KEY=d3k100pr01qtciv0v8hgd3k100pr01qtciv0v8i0")
            print("   - ALPHAVANTAGE_KEY=5BPNWBD7BEPLFK2R")

if __name__ == "__main__":
    asyncio.run(main())


