"""
Service to load sample data - can be called from API endpoints.
Uses the robust multi-source data fetcher.
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from pathlib import Path

from fredapi import Fred
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
import pandas as pd

from app.db import SessionLocal
from app.models import Ticker, PriceDaily, RiskFreeSeries
from app.services.data_sources import StockDataFetcher

logger = logging.getLogger(__name__)

import os
FRED_API_KEY = os.getenv("FRED_API_KEY", "your_fred_api_key_here")


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
        
        result = await session.execute(
            select(Ticker.id).where(Ticker.symbol == symbol)
        )
        ticker_id = result.scalar_one_or_none()
        return ticker_id


async def insert_price_data(session, ticker_id, history_df, pe, market_cap, avg_volume):
    """Insert price data with UPSERT logic."""
    try:
        price_rows = []
        for date_idx, row in history_df.iterrows():
            price_rows.append({
                'ticker_id': ticker_id,
                'date': date_idx.date(),
                'open': float(row['Open']) if not pd.isna(row['Open']) else None,
                'high': float(row['High']) if not pd.isna(row['High']) else None,
                'low': float(row['Low']) if not pd.isna(row['Low']) else None,
                'close': float(row['Close']) if not pd.isna(row['Close']) else None,
                'volume': int(row['Volume']) if not pd.isna(row['Volume']) else None,
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
                return 0
            
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
                logger.info(f"Inserted {len(risk_free_rows)} risk-free rate entries")
                return len(risk_free_rows)
        except Exception as fred_error:
            logger.warning(f"FRED API error: {fred_error}. Using placeholder data...")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5*365)
            current_date = start_date
            risk_free_rows = []
            
            while current_date <= end_date:
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
                logger.info(f"Inserted {len(risk_free_rows)} placeholder risk-free rate entries")
                return len(risk_free_rows)
            
    except Exception as e:
        await session.rollback()
        logger.error(f"Error inserting risk-free data: {e}")
        return 0


async def load_sample_data(symbols: list[str] = None):
    """
    Load sample data for given symbols using robust multi-source fetcher.
    Can be called from API endpoints to refresh data.
    
    Args:
        symbols: List of ticker symbols to load. If None, uses default list.
        
    Returns:
        dict: Statistics about loaded data
    """
    if symbols is None:
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    logger.info(f"Loading data for {len(symbols)} symbols...")
    
    fetcher = StockDataFetcher()
    ticker_count = 0
    price_count = 0
    skipped_count = 0
    
    async with SessionLocal() as session:
        for symbol in symbols:
            try:
                logger.info(f"Processing {symbol}...")
                
                # Use robust fetcher with fallbacks
                data, has_partial = await fetcher.fetch_stock_data(symbol)
                
                if data is None:
                    skipped_count += 1
                    continue
                
                ticker_id = await insert_ticker(
                    session, 
                    data['symbol'], 
                    data['name'], 
                    data['exchange']
                )
                
                if ticker_id:
                    ticker_count += 1
                    
                    rows_inserted = await insert_price_data(
                        session,
                        ticker_id,
                        data['history'],
                        data['pe'],
                        data['market_cap'],
                        data['avg_volume']
                    )
                    price_count += rows_inserted
                    logger.info(f"✓ {symbol}: {rows_inserted} price records (source: {data['source']})")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                skipped_count += 1
                continue
        
        risk_free_count = await fetch_and_insert_risk_free_data(session)
    
    return {
        'tickers': ticker_count,
        'prices': price_count,
        'risk_free': risk_free_count,
        'skipped': skipped_count
    }

