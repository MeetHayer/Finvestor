"""
Robust seed script to populate ticker, price_daily, and risk_free_series tables
with 5 years of historical data from multiple sources with comprehensive fallback.
"""
import asyncio
import sys
import json
import traceback
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from fredapi import Fred
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal, engine, Base
from app.models import Ticker, PriceDaily, RiskFreeSeries
from app.services.data_sources import StockDataFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get API keys from environment
import os
FRED_API_KEY = os.getenv("FRED_API_KEY", "your_fred_api_key_here")


class SeedingStats:
    """Track seeding statistics."""
    def __init__(self):
        self.successful = []
        self.partial_fundamentals = []
        self.failed = []
        self.total_price_rows = 0
        self.risk_free_rows = 0
        self.errors = []


async def insert_ticker(session, symbol: str, name: str, exchange: str):
    """Insert or update ticker and return ticker_id."""
    try:
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
        ticker_id = result.scalar_one()
        return ticker_id
    except Exception as e:
        await session.rollback()
        logger.error(f"Error inserting ticker {symbol}: {e}")
        
        # Fallback: select existing ticker
        result = await session.execute(
            select(Ticker.id).where(Ticker.symbol == symbol)
        )
        ticker_id = result.scalar_one_or_none()
        return ticker_id


async def insert_price_data(session, ticker_id, history_df, pe, market_cap, avg_volume):
    """Insert price data with UPSERT logic."""
    try:
        price_rows = []
        
        # Normalize column names (handle different data sources)
        hist_normalized = history_df.copy()
        if 'Open' in hist_normalized.columns:
            hist_normalized.columns = [col.lower() for col in hist_normalized.columns]
        
        for date_idx, row in hist_normalized.iterrows():
            # Handle timezone-aware dates
            if hasattr(date_idx, 'date'):
                date_val = date_idx.date()
            else:
                date_val = pd.to_datetime(date_idx).date()
            
            price_rows.append({
                'ticker_id': ticker_id,
                'date': date_val,
                'open': float(row['open']) if 'open' in row and not pd.isna(row['open']) else None,
                'high': float(row['high']) if 'high' in row and not pd.isna(row['high']) else None,
                'low': float(row['low']) if 'low' in row and not pd.isna(row['low']) else None,
                'close': float(row['close']) if 'close' in row and not pd.isna(row['close']) else None,
                'volume': int(row['volume']) if 'volume' in row and not pd.isna(row['volume']) else None,
                'avg_volume': avg_volume,
                'pe': float(pe) if pe and not pd.isna(pe) else None,
                'market_cap': market_cap
            })
        
        if price_rows:
            stmt = pg_insert(PriceDaily).values(price_rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker_id', 'date'],
                set_=dict(
                    open=stmt.excluded.open,
                    high=stmt.excluded.high,
                    low=stmt.excluded.low,
                    close=stmt.excluded.close,
                    volume=stmt.excluded.volume,
                    avg_volume=stmt.excluded.avg_volume,
                    pe=stmt.excluded.pe,
                    market_cap=stmt.excluded.market_cap
                )
            )
            await session.execute(stmt)
            await session.commit()
            return len(price_rows)
    except Exception as e:
        await session.rollback()
        logger.error(f"Error inserting price data for ticker_id {ticker_id}: {e}")
        traceback.print_exc()
        return 0


async def fetch_and_insert_risk_free_data(session):
    """Fetch 3-month T-Bill data from FRED and insert into risk_free_series."""
    try:
        logger.info("Fetching risk-free rate data from FRED...")
        
        try:
            fred = Fred(api_key=FRED_API_KEY)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5*365)
            
            data = fred.get_series('DGS3MO', start_date, end_date)
            
            if data.empty:
                logger.warning("No FRED data available, using placeholder rates...")
                return await insert_placeholder_risk_free_data(session)
            
            risk_free_rows = []
            for date_idx, rate in data.items():
                if not pd.isna(rate):
                    risk_free_rows.append({
                        'date': date_idx.date(),
                        'rate': float(rate) / 100
                    })
            
            if risk_free_rows:
                stmt = pg_insert(RiskFreeSeries).values(risk_free_rows)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['date'],
                    set_=dict(rate=stmt.excluded.rate)
                )
                await session.execute(stmt)
                await session.commit()
                logger.info(f"✓ Inserted {len(risk_free_rows)} risk-free rate entries")
                return len(risk_free_rows)
        except Exception as fred_error:
            logger.warning(f"FRED API error: {fred_error}. Using placeholder data...")
            return await insert_placeholder_risk_free_data(session)
            
    except Exception as e:
        await session.rollback()
        logger.error(f"Error inserting risk-free data: {e}")
        return 0


async def insert_placeholder_risk_free_data(session):
    """Insert placeholder risk-free rate data."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)
    current_date = start_date
    risk_free_rows = []
    
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() < 5:
            risk_free_rows.append({
                'date': current_date.date(),
                'rate': 0.02
            })
        current_date += timedelta(days=1)
    
    if risk_free_rows:
        stmt = pg_insert(RiskFreeSeries).values(risk_free_rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=['date'],
            set_=dict(rate=stmt.excluded.rate)
        )
        await session.execute(stmt)
        await session.commit()
        logger.info(f"✓ Inserted {len(risk_free_rows)} placeholder risk-free rate entries")
        return len(risk_free_rows)
    return 0


async def seed_database(symbols: list[str] = None, on_demand: bool = False):
    """
    Main seeding function with comprehensive error handling.
    
    Args:
        symbols: List of ticker symbols to process
        on_demand: If True, only process requested symbols without bulk seeding
    """
    logger.info("="*70)
    logger.info("🚀 Starting Finvestor Data Seeding")
    logger.info("="*70)
    
    stats = SeedingStats()
    fetcher = StockDataFetcher()
    
    # Read tickers from file if not provided
    if symbols is None:
        tickers_file = Path(__file__).parent / "sample_tickers.txt"
        if not tickers_file.exists():
            logger.error(f"❌ Tickers file not found: {tickers_file}")
            return stats
        
        with open(tickers_file, 'r') as f:
            symbols = [line.strip() for line in f if line.strip()]
    
    logger.info(f"📊 Processing {len(symbols)} symbols...")
    logger.info("")
    
    commit_counter = 0
    
    async with SessionLocal() as session:
        for idx, symbol in enumerate(symbols, 1):
            try:
                logger.info(f"[{idx}/{len(symbols)}] {symbol}")
                
                # Fetch data with comprehensive fallback
                data, has_partial = await fetcher.fetch_stock_data(symbol)
                
                if data is None:
                    stats.failed.append(symbol)
                    logger.error(f"  ❌ FAILED: {symbol}")
                    continue
                
                # Insert ticker
                ticker_id = await insert_ticker(
                    session, 
                    data['symbol'], 
                    data['name'], 
                    data['exchange']
                )
                
                if not ticker_id:
                    stats.failed.append(symbol)
                    logger.error(f"  ❌ FAILED to insert ticker: {symbol}")
                    continue
                
                # Insert price data
                rows_inserted = await insert_price_data(
                    session,
                    ticker_id,
                    data['history'],
                    data['pe'],
                    data['market_cap'],
                    data['avg_volume']
                )
                
                stats.total_price_rows += rows_inserted
                
                if has_partial:
                    stats.partial_fundamentals.append(symbol)
                    logger.info(f"  ✓ SUCCESS: {rows_inserted} rows (source: {data['source']}) ⚠️ Partial fundamentals")
                else:
                    stats.successful.append(symbol)
                    logger.info(f"  ✓ SUCCESS: {rows_inserted} rows (source: {data['source']})")
                
                commit_counter += 1
                if commit_counter % 5 == 0:
                    logger.info(f"  💾 Committed batch (every 5 tickers)")
                
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                error_trace = traceback.format_exc()
                stats.failed.append(symbol)
                stats.errors.append({
                    'symbol': symbol,
                    'error': str(e),
                    'traceback': error_trace
                })
                logger.error(f"  ❌ Exception processing {symbol}: {e}")
                logger.debug(error_trace)
                continue
        
        # Fetch and insert risk-free rate data
        logger.info("")
        logger.info("📈 Fetching risk-free rates...")
        stats.risk_free_rows = await fetch_and_insert_risk_free_data(session)
    
    # Combine fetcher errors with stats errors
    stats.errors.extend(fetcher.errors)
    
    # Write error log
    await write_error_log(stats, fetcher)
    
    # Print summary
    print_summary(stats)
    
    return stats


async def write_error_log(stats: SeedingStats, fetcher: StockDataFetcher):
    """Write detailed error log to file."""
    error_log_path = Path(__file__).parent / "error_log.txt"
    
    with open(error_log_path, 'w') as f:
        f.write("="*70 + "\n")
        f.write(f"Finvestor Seeding Error Log\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Total Errors: {len(stats.errors)}\n\n")
        
        if stats.errors:
            f.write("Detailed Errors:\n")
            f.write("-"*70 + "\n")
            for error in stats.errors:
                f.write(f"\nSymbol: {error.get('symbol', 'UNKNOWN')}\n")
                f.write(f"Source: {error.get('source', 'UNKNOWN')}\n")
                f.write(f"Error: {error.get('error', 'N/A')}\n")
                if 'strategy' in error:
                    f.write(f"Strategy: {error['strategy']}\n")
                if 'traceback' in error:
                    f.write(f"Traceback:\n{error['traceback']}\n")
                f.write("-"*70 + "\n")
        
        f.write("\n\nJSON Format:\n")
        f.write(json.dumps(stats.errors, indent=2))
    
    logger.info(f"📝 Error log written to: {error_log_path}")


def print_summary(stats: SeedingStats):
    """Print comprehensive summary."""
    print("\n")
    print("="*70)
    print("📊 SEEDING SUMMARY")
    print("="*70)
    print()
    
    # Successful tickers
    print(f"✅ Successful tickers: {len(stats.successful)}")
    if stats.successful:
        print(f"   {', '.join(stats.successful[:10])}")
        if len(stats.successful) > 10:
            print(f"   ... and {len(stats.successful) - 10} more")
    print()
    
    # Partial fundamentals
    print(f"⚠️  Partial fundamentals missing: {len(stats.partial_fundamentals)}")
    if stats.partial_fundamentals:
        print(f"   {', '.join(stats.partial_fundamentals[:10])}")
        if len(stats.partial_fundamentals) > 10:
            print(f"   ... and {len(stats.partial_fundamentals) - 10} more")
    print()
    
    # Failed tickers
    print(f"❌ Failed tickers: {len(stats.failed)}")
    if stats.failed:
        print(f"   {', '.join(stats.failed[:10])}")
        if len(stats.failed) > 10:
            print(f"   ... and {len(stats.failed) - 10} more")
    print()
    
    # Data summary
    print(f"📈 Total price rows inserted: {stats.total_price_rows}")
    print(f"📉 Risk-free rate entries: {stats.risk_free_rows}")
    print()
    
    if stats.failed:
        print("⚠️  Unable to seed some symbols. Check seed/error_log.txt for details.")
        print("   Copy the contents and paste to ChatGPT for diagnostic help.")
    
    print("="*70)
    print(f"\n✅ Seeding complete – {len(stats.successful) + len(stats.partial_fundamentals)} tickers, "
          f"{stats.total_price_rows} price rows, {stats.risk_free_rows} risk-free entries")
    print()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Seed Finvestor database with stock data')
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Specific symbols to fetch (space-separated)'
    )
    parser.add_argument(
        '--on-demand',
        action='store_true',
        help='On-demand mode: only fetch requested symbols, skip bulk seeding'
    )
    
    args = parser.parse_args()
    
    if args.on_demand:
        if not args.symbols:
            print("❌ Error: --on-demand requires --symbols")
            sys.exit(1)
        logger.info("🎯 On-demand mode: fetching only requested symbols")
    
    asyncio.run(seed_database(symbols=args.symbols, on_demand=args.on_demand))


if __name__ == "__main__":
    main()
