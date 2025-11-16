"""
Seed database with REAL data using MULTIPLE sources:
1. yahoo-fin (yahoo_fin.stock_info)
2. investpy
3. yfinance
4. marketdata (if available)
All with fallback logic
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db import SessionLocal
from app.models import Ticker, PriceDaily

SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA']

async def seed_with_yahoo_fin(session, symbol: str):
    """Try yahoo-fin library"""
    try:
        from yahoo_fin import stock_info as si
        print(f"  ↳ Trying yahoo-fin...")
        
        # Get historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        hist = si.get_data(symbol, start_date=start_date, end_date=end_date)
        
        if hist is None or len(hist) == 0:
            return None
        
        # Get company info
        try:
            info = si.get_quote_table(symbol)
            name = info.get('Long Name', symbol) if isinstance(info, dict) else symbol
        except:
            name = symbol
        
        return {
            'symbol': symbol,
            'name': name,
            'exchange': 'UNKNOWN',
            'history': hist,
            'source': 'yahoo-fin'
        }
    except ImportError:
        print(f"  ↳ yahoo-fin not available")
        return None
    except Exception as e:
        print(f"  ↳ yahoo-fin failed: {str(e)[:80]}")
        return None

async def seed_with_investpy(session, symbol: str):
    """Try investpy"""
    try:
        import investpy
        print(f"  ↳ Trying investpy...")
        
        # Investpy uses country and stock name format
        # For US stocks, country is 'united states'
        try:
            hist = investpy.get_stock_historical_data(
                stock=symbol,
                country='united states',
                from_date=datetime.now().strftime('%d/%m/%Y'),
                to_date=(datetime.now() - timedelta(days=365)).strftime('%d/%m/%Y')
            )
        except:
            # Try without country if format differs
            hist = investpy.get_stock_historical_data(
                stock=symbol,
                country='United States',
                from_date=(datetime.now() - timedelta(days=365)).strftime('%d/%m/%Y'),
                to_date=datetime.now().strftime('%d/%m/%Y')
            )
        
        if hist is None or len(hist) == 0:
            return None
        
        return {
            'symbol': symbol,
            'name': symbol,
            'exchange': 'UNKNOWN',
            'history': hist,
            'source': 'investpy'
        }
    except ImportError:
        print(f"  ↳ investpy not available")
        return None
    except Exception as e:
        print(f"  ↳ investpy failed: {str(e)[:80]}")
        return None

async def seed_with_yfinance(session, symbol: str):
    """Try yfinance with better handling"""
    try:
        import yfinance as yf
        print(f"  ↳ Trying yfinance...")
        
        ticker = yf.Ticker(symbol)
        
        # Try different periods
        for period in ['1y', '6mo', '3mo']:
            try:
                hist = ticker.history(period=period)
                if hist is not None and len(hist) > 0:
                    # Try to get name
                    try:
                        name = ticker.info.get('longName') or ticker.info.get('shortName') or symbol
                    except:
                        name = symbol
                    
                    return {
                        'symbol': symbol,
                        'name': name,
                        'exchange': 'UNKNOWN',
                        'history': hist,
                        'source': f'yfinance-{period}'
                    }
            except:
                continue
        
        return None
    except ImportError:
        print(f"  ↳ yfinance not available")
        return None
    except Exception as e:
        print(f"  ↳ yfinance failed: {str(e)[:80]}")
        return None

async def insert_ticker_and_prices(session, data):
    """Insert ticker and price data"""
    if data is None:
        return 0
    
    # Insert ticker
    ticker_stmt = pg_insert(Ticker).values(
        symbol=data['symbol'],
        name=data['name'],
        exchange=data['exchange']
    ).on_conflict_do_update(
        index_elements=['symbol'],
        set_=dict(name=data['name'], exchange=data['exchange'])
    ).returning(Ticker.id)
    
    result = await session.execute(ticker_stmt)
    ticker_id = result.scalar_one()
    await session.commit()
    
    # Insert prices
    hist = data['history']
    price_rows = []
    
    for date_idx, row in hist.iterrows():
        date_val = date_idx.date() if hasattr(date_idx, 'date') else pd.to_datetime(date_idx).date()
        
        # Handle different column name formats
        open_val = row.get('Open', row.get('open', row.get('Open Price', None)))
        high_val = row.get('High', row.get('high', row.get('High Price', None)))
        low_val = row.get('Low', row.get('low', row.get('Low Price', None)))
        close_val = row.get('Close', row.get('close', row.get('Close Price', row.get('Price', None))))
        volume_val = row.get('Volume', row.get('volume', row.get('Volume', 0)))
        
        if close_val is None:
            continue
        
        price_rows.append({
            'ticker_id': ticker_id,
            'date': date_val,
            'open': float(open_val) if pd.notna(open_val) and open_val is not None else None,
            'high': float(high_val) if pd.notna(high_val) and high_val is not None else None,
            'low': float(low_val) if pd.notna(low_val) and low_val is not None else None,
            'close': float(close_val) if pd.notna(close_val) else None,
            'volume': int(volume_val) if pd.notna(volume_val) else 0,
            'pe': None,
            'market_cap': None,
        })
    
    if price_rows:
        price_stmt = pg_insert(PriceDaily).values(price_rows)
        price_stmt = price_stmt.on_conflict_do_nothing()
        await session.execute(price_stmt)
        await session.commit()
    
    return len(price_rows)

async def seed_ticker(session, symbol: str):
    """Try all sources for a ticker"""
    print(f"\n📈 Fetching {symbol}...")
    
    # Try sources in order
    sources = [
        seed_with_yahoo_fin,
        seed_with_yfinance,
        seed_with_investpy,
    ]
    
    for source_func in sources:
        data = await source_func(session, symbol)
        if data:
            rows = await insert_ticker_and_prices(session, data)
            if rows > 0:
                print(f"  ✅ SUCCESS: {rows} rows from {data['source']}")
                return True
    
    print(f"  ❌ FAILED: No data from any source")
    return False

async def main():
    """Seed with all sources"""
    print("🚀 Seeding REAL data using multiple sources...")
    print("📊 Sources: yahoo-fin → yfinance → investpy")
    print(f"📈 Symbols: {', '.join(SYMBOLS)}\n")
    
    async with SessionLocal() as session:
        success_count = 0
        for idx, symbol in enumerate(SYMBOLS, 1):
            if await seed_ticker(session, symbol):
                success_count += 1
            await asyncio.sleep(1)  # Rate limit delay
        
        print(f"\n{'='*60}")
        print(f"✅ Complete: {success_count}/{len(SYMBOLS)} symbols seeded")
        
        if success_count == 0:
            print("\n❌ ISSUE: All sources failed")
            print("Possible reasons:")
            print("  1. Libraries not installed properly")
            print("  2. Network/API blocking")
            print("  3. Symbol format issues")
            print("  4. Date format problems")

if __name__ == "__main__":
    asyncio.run(main())


