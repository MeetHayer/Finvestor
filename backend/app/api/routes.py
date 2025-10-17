from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from datetime import date
import logging

from app.db import get_session
from app.services.market_data import get_market_data_fetcher
from app.services.benchmarks_live import get_all_benchmarks

router = APIRouter(prefix="/api")
log = logging.getLogger(__name__)

@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    # DB ping (non-fatal)
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_ok = False
        log.exception("DB ping failed")
    return {"status": "ok", "db": db_ok}

@router.get("/benchmarks")
async def get_benchmarks():
    """Get real benchmark data from multiple sources"""
    try:
        benchmarks = await get_all_benchmarks()
        return benchmarks
    except Exception as e:
        log.exception(f"Failed to fetch benchmarks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch benchmark data: {e}")

# -------- Search (DB optional; fallback to yfinance single) --------
@router.get("/search")
async def search(q: str = Query(..., min_length=1), session: AsyncSession = Depends(get_session)):
    like = f"%{q.upper()}%"
    try:
        # Use your existing ticker table
        res = await session.execute(text("""
            SELECT symbol, COALESCE(name, symbol) AS name, 'DB' AS source
            FROM ticker
            WHERE UPPER(symbol) LIKE :s OR UPPER(name) LIKE :s
            ORDER BY symbol
            LIMIT 25
        """), {"s": like})
        rows = [dict(r._mapping) for r in res.fetchall()]
        if rows:
            return rows
    except Exception as e:
        log.exception(f"DB search failed: {e}")
        pass
    
    # fallback to yfinance only if DB search fails
    import yfinance as yf
    try:
        t = yf.Ticker(q.upper())
        info = t.info or {}
        return [{"symbol": q.upper(), "name": info.get("shortName") or info.get("longName") or q.upper(), "source": "yf"}]
    except Exception:
        return [{"symbol": q.upper(), "name": q.upper(), "source": "raw"}]

# -------- Market data (USE YOUR REAL DATABASE ONLY) --------
@router.get("/data/{symbol}")
async def data(symbol: str, range_days: int = 365, session: AsyncSession = Depends(get_session)):
    log.info(f"Fetching data for {symbol} from YOUR REAL DATABASE")
    
    try:
        # Get price data from YOUR database (get latest N rows, then sort ASC for chart)
        res = await session.execute(text("""
            SELECT pd.date, pd.open, pd.high, pd.low, pd.close, pd.volume
            FROM (
                SELECT pd.date, pd.open, pd.high, pd.low, pd.close, pd.volume
                FROM price_daily pd
                JOIN ticker t ON pd.ticker_id = t.id
                WHERE t.symbol = :sym 
                ORDER BY pd.date DESC 
                LIMIT :limit
            ) pd
            ORDER BY pd.date ASC
        """), {"sym": symbol.upper(), "limit": range_days})
        
        rows = res.fetchall()
        if rows and len(rows) > 0:
            log.info(f"Found {len(rows)} REAL rows for {symbol} in YOUR database")
            
            # Convert to the expected format
            ohlc = []
            from datetime import datetime
            
            for row in rows:
                # Convert date to timestamp milliseconds
                if hasattr(row.date, 'timestamp'):
                    date_ms = int(row.date.timestamp() * 1000)
                else:
                    # For date objects, convert to datetime at midnight UTC
                    dt = datetime.combine(row.date, datetime.min.time())
                    date_ms = int(dt.timestamp() * 1000)
                
                ohlc.append([
                    date_ms,
                    float(row.open or 0),
                    float(row.high or 0),
                    float(row.low or 0),
                    float(row.close),
                    int(row.volume or 0)
                ])
            
            # Get latest and previous close from YOUR REAL DATA (ASC order, so last is latest)
            latest_close = float(rows[-1].close)  # Last row is latest
            prev_close = float(rows[-2].close) if len(rows) > 1 else latest_close  # Second to last is previous
            
            # Get fundamentals from YOUR database first, then API fallbacks
            fundamentals = {}
            try:
                fund_res = await session.execute(text("""
                    SELECT fc.pe_ratio, fc.market_cap, fc.week_52_high, fc.week_52_low
                    FROM fundamentals_cache fc
                    JOIN ticker t ON fc.ticker_id = t.id
                    WHERE t.symbol = :sym 
                    ORDER BY fc.updated_at DESC 
                    LIMIT 1
                """), {"sym": symbol.upper()})
                
                fund_row = fund_res.first()
                if fund_row:
                    fundamentals = {
                        "trailingPE": float(fund_row.pe_ratio) if fund_row.pe_ratio else None,
                        "marketCap": int(fund_row.market_cap) if fund_row.market_cap else None,
                        "fiftyTwoWeekHigh": float(fund_row.week_52_high) if fund_row.week_52_high else None,
                        "fiftyTwoWeekLow": float(fund_row.week_52_low) if fund_row.week_52_low else None,
                    }
                    log.info(f"Got fundamentals from YOUR database for {symbol}")
            except Exception as fund_e:
                log.warning(f"Database fundamentals failed for {symbol}: {fund_e}")
            
            # If no fundamentals in database, try API fallbacks
            if not fundamentals or not any(fundamentals.values()):
                log.info(f"Fetching fundamentals from API fallbacks for {symbol}")
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(symbol.upper())
                    info = ticker.info or {}
                    
                    # Calculate 52-week high/low from your price data
                    all_highs = [float(row.high) for row in rows]
                    all_lows = [float(row.low) for row in rows]
                    
                    fundamentals = {
                        "trailingPE": info.get('trailingPE'),
                        "marketCap": info.get('marketCap'),
                        "fiftyTwoWeekHigh": float(max(all_highs)) if all_highs else None,
                        "fiftyTwoWeekLow": float(min(all_lows)) if all_lows else None,
                        "beta": info.get('beta'),
                        "dividendYield": info.get('dividendYield'),
                    }
                    log.info(f"Got fundamentals from API for {symbol}")
                except Exception as api_e:
                    log.warning(f"API fundamentals failed for {symbol}: {api_e}")
                    # Use calculated values from your price data
                    all_highs = [float(row.high) for row in rows]
                    all_lows = [float(row.low) for row in rows]
                    fundamentals = {
                        "trailingPE": None,
                        "marketCap": None,
                        "fiftyTwoWeekHigh": float(max(all_highs)) if all_highs else None,
                        "fiftyTwoWeekLow": float(min(all_lows)) if all_lows else None,
                        "beta": None,
                        "dividendYield": None,
                    }
            
            return {
                "symbol": symbol.upper(),
                "latest": {"close": latest_close, "prevClose": prev_close},
                "ohlc": ohlc,
                "fundamentals": fundamentals,
            }
        else:
            log.warning(f"No data found in YOUR database for {symbol}")
            raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found in database")
    except Exception as e:
        log.exception(f"Database fetch failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error for {symbol}: {e}")

# Watchlist and Portfolio endpoints are now in portfolios_watchlists.py