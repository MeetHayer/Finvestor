from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from datetime import date
import logging
from pydantic import BaseModel

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
    qu = q.upper()
    starts = f"{qu}%"
    contains = f"%{qu}%"
    # Prioritize: 1) symbol starts with query, 2) symbol contains query
    try:
        res = await session.execute(text("""
            SELECT symbol, COALESCE(name, symbol) AS name, 'DB' AS source,
                   CASE 
                     WHEN UPPER(symbol) LIKE :starts THEN 1
                     WHEN UPPER(name) LIKE :starts THEN 2
                     ELSE 3
                   END AS priority
            FROM ticker
            WHERE UPPER(symbol) LIKE :contains OR UPPER(name) LIKE :contains
            ORDER BY priority, symbol
            LIMIT 25
        """), {"starts": starts, "contains": contains})
        return [{"symbol": r.symbol, "name": r.name, "source": r.source} for r in res.fetchall()]
    except Exception as e:
        log.exception(f"DB search failed: {e}")
        # On error, return empty list to avoid suggesting unknown symbols
        return []

async def auto_seed_missing_prices(symbol: str, session: AsyncSession):
    """
    Check if price data is up-to-date and seed missing dates if needed.
    Returns True if seeding was performed, False otherwise.
    """
    from datetime import datetime, date, timedelta
    import requests
    import os
    
    try:
        # Get ticker_id and latest date we have
        res = await session.execute(text("""
            SELECT t.id, MAX(pd.date) as latest_date
            FROM ticker t
            LEFT JOIN price_daily pd ON t.id = pd.ticker_id
            WHERE t.symbol = :sym
            GROUP BY t.id
        """), {"sym": symbol.upper()})
        
        row = res.first()
        if not row:
            log.warning(f"Ticker {symbol} not found in database")
            return False
        
        ticker_id = row.id
        latest_date = row.latest_date
        
        # Determine last business day (today or Friday if weekend)
        today = date.today()
        last_business_day = today
        
        # If weekend, go back to Friday
        if today.weekday() == 5:  # Saturday
            last_business_day = today - timedelta(days=1)
        elif today.weekday() == 6:  # Sunday
            last_business_day = today - timedelta(days=2)
        
        # If we have data up to last business day, no need to seed
        if latest_date and latest_date >= last_business_day:
            log.info(f"{symbol}: Data is up-to-date (latest: {latest_date}, last_business_day: {last_business_day})")
            return False
        
        # Calculate how many days we're missing
        if latest_date:
            days_missing = (last_business_day - latest_date).days
            start_date = latest_date + timedelta(days=1)
        else:
            # No data at all, fetch last 365 days
            days_missing = 365
            start_date = last_business_day - timedelta(days=365)
        
        log.info(f"{symbol}: Missing {days_missing} days of data (from {start_date} to {last_business_day})")
        
        # Fetch missing data
        # 1) Alpha Vantage daily
        av_key = os.getenv('ALPHA_VANTAGE_KEY') or os.getenv('ALPHAVANTAGE_KEY')
        inserted_count = 0
        if av_key:
            try:
                url = "https://www.alphavantage.co/query"
                params = {
                    'function': 'TIME_SERIES_DAILY',
                    'symbol': symbol.upper(),
                    'apikey': av_key,
                    'outputsize': 'full' if days_missing > 100 else 'compact'
                }
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                ts = data.get('Time Series (Daily)', {})
                if ts:
                    for date_str, price_data in ts.items():
                        price_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        if latest_date and price_date <= latest_date: continue
                        if price_date > last_business_day: continue
                        try:
                            await session.execute(text("""
                                INSERT INTO price_daily (ticker_id, date, open, high, low, close, volume)
                                VALUES (:ticker_id, :date, :open, :high, :low, :close, :volume)
                                ON CONFLICT (ticker_id, date) DO NOTHING
                            """), {
                                "ticker_id": ticker_id,
                                "date": price_date,
                                "open": float(price_data['1. open']),
                                "high": float(price_data['2. high']),
                                "low": float(price_data['3. low']),
                                "close": float(price_data['4. close']),
                                "volume": int(price_data['5. volume'])
                            })
                            inserted_count += 1
                        except Exception as e:
                            log.error(f"Insert error AV {symbol} {date_str}: {e}")
                    await session.commit()
                    if inserted_count:
                        log.info(f"✅ AV seeded {inserted_count} days for {symbol}")
                        return True
            except Exception as e:
                log.warning(f"AV fetch failed for {symbol}: {e}")

        # 2) Finnhub (daily candles)
        try:
            fk = os.getenv('FINNHUB_KEY') or os.getenv('FINNHUB_API_KEY')
            if fk:
                import time
                frm = int(time.mktime(start_date.timetuple()))
                to = int(time.mktime(last_business_day.timetuple()))
                r = requests.get('https://finnhub.io/api/v1/stock/candle', params={'symbol': symbol.upper(), 'resolution': 'D', 'from': frm, 'to': to, 'token': fk}, timeout=15)
                j = r.json()
                if j and j.get('s') == 'ok':
                    for i, dts in enumerate(j.get('t', [])):
                        price_date = datetime.fromtimestamp(dts).date()
                        if latest_date and price_date <= latest_date: continue
                        if price_date > last_business_day: continue
                        o,h,l,c,v = j['o'][i], j['h'][i], j['l'][i], j['c'][i], j['v'][i]
                        try:
                            await session.execute(text("""
                                INSERT INTO price_daily (ticker_id, date, open, high, low, close, volume)
                                VALUES (:ticker_id, :date, :open, :high, :low, :close, :volume)
                                ON CONFLICT (ticker_id, date) DO NOTHING
                            """), {"ticker_id": ticker_id, "date": price_date, "open": o, "high": h, "low": l, "close": c, "volume": v})
                            inserted_count += 1
                        except Exception as e:
                            log.error(f"Insert error FH {symbol} {price_date}: {e}")
                    await session.commit()
                    if inserted_count:
                        log.info(f"✅ Finnhub seeded {inserted_count} days for {symbol}")
                        return True
        except Exception as e:
            log.warning(f"Finnhub fetch failed for {symbol}: {e}")

        # 3) yfinance 2-year window
        try:
            import yfinance as yf
            start = last_business_day - timedelta(days=730)
            df = yf.Ticker(symbol.upper()).history(start=start, end=last_business_day + timedelta(days=1), interval='1d', auto_adjust=False)
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    d = idx.date()
                    if latest_date and d <= latest_date: continue
                    if d > last_business_day: continue
                    o,h,l,c,v = row['Open'], row['High'], row['Low'], row['Close'], row['Volume']
                    try:
                        await session.execute(text("""
                            INSERT INTO price_daily (ticker_id, date, open, high, low, close, volume)
                            VALUES (:ticker_id, :date, :open, :high, :low, :close, :volume)
                            ON CONFLICT (ticker_id, date) DO NOTHING
                        """), {"ticker_id": ticker_id, "date": d, "open": float(o) if o==o else None, "high": float(h) if h==h else None, "low": float(l) if l==l else None, "close": float(c) if c==c else None, "volume": int(v) if v==v else None})
                        inserted_count += 1
                    except Exception as e:
                        log.error(f"Insert error YF {symbol} {d}: {e}")
                await session.commit()
                if inserted_count:
                    log.info(f"✅ yfinance seeded {inserted_count} days for {symbol}")
                    return True
        except Exception as e:
            log.warning(f"yfinance fetch failed for {symbol}: {e}")

        # TODO: Add yahooquery / yahoo_fin / investpy fallbacks similarly if needed
        return False
        
    except Exception as e:
        log.error(f"Auto-seed failed for {symbol}: {e}")
        await session.rollback()
        return False


# -------- Market data (USE YOUR REAL DATABASE ONLY) --------
@router.get("/data/{symbol}")
async def data(symbol: str, range_days: int = 365, refresh: bool = False, session: AsyncSession = Depends(get_session)):
    log.info(f"Fetching data for {symbol} from YOUR REAL DATABASE")
    try:
        # If refresh requested, fetch ~last 400d for just this symbol and upsert
        if refresh:
            from app.services.market_data import fetch_daily_history, upsert_history_db
            rows_live = await fetch_daily_history(symbol, days=420)
            await upsert_history_db(session, symbol, rows_live)

        # Read from DB (latest N rows → ASC for chart)
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

        if not rows or len(rows) == 0:
            log.info(f"No price data in DB for {symbol}, attempting fetch from external APIs")
            # Try fetch_daily_history first (yfinance, etc.)
            from app.services.market_data import fetch_daily_history, upsert_history_db
            try:
                rows_live = await fetch_daily_history(symbol, days=420)
                await upsert_history_db(session, symbol, rows_live)
                res = await session.execute(text("""
                    SELECT pd.date, pd.open, pd.high, pd.low, pd.close, pd.volume
                    FROM price_daily pd JOIN ticker t ON t.id=pd.ticker_id
                    WHERE t.symbol=:sym ORDER BY pd.date ASC
                """), {"sym": symbol.upper()})
                rows = res.fetchall()
            except Exception as e:
                log.warning(f"fetch_daily_history failed for {symbol}: {e}, trying Alpha Vantage/Finnhub fallback")
                # Fallback to Alpha Vantage / Finnhub (benchmark APIs) for 1-year history
                rows = []  # Reset rows for fallback attempts
                try:
                    from app.services.benchmarks_live import get_last_business_day_prices_alpha_vantage, get_last_business_day_prices_finnhub
                    import os, requests
                    from datetime import datetime, timedelta
                    
                    # Try Alpha Vantage full 1-year data
                    av_key = os.getenv('ALPHA_VANTAGE_KEY') or os.getenv('ALPHAVANTAGE_KEY')
                    log.info(f"Alpha Vantage key available: {bool(av_key)}")
                    if av_key:
                        try:
                            log.info(f"Fetching {symbol} from Alpha Vantage...")
                            r = requests.get('https://www.alphavantage.co/query',
                                params={'function':'TIME_SERIES_DAILY','symbol':symbol.upper(),'apikey':av_key,'outputsize':'full'},
                                timeout=15)
                            resp_data = r.json() or {}
                            log.info(f"AV response keys: {list(resp_data.keys())}")
                            ts = resp_data.get('Time Series (Daily)',{})
                            if ts:
                                rows_to_insert = []
                                for ds, pd_data in list(ts.items())[:365]:  # last 1 year
                                    d = datetime.strptime(ds, "%Y-%m-%d").date()
                                    rows_to_insert.append({
                                        "date": d, 
                                        "open": float(pd_data['1. open']), 
                                        "high": float(pd_data['2. high']),
                                        "low": float(pd_data['3. low']), 
                                        "close": float(pd_data['4. close']),
                                        "volume": int(pd_data.get('5. volume',0) or 0)
                                    })
                                if rows_to_insert:
                                    await upsert_history_db(session, symbol, rows_to_insert)
                                    # Try to fetch company name/description from fundamentals service
                                    try:
                                        from app.services.fundamentals import fundamentals_service
                                        fund = await fundamentals_service.get_fundamentals(symbol.upper())
                                        comp_name = fund.get('longName') or fund.get('shortName')
                                        if comp_name:
                                            await session.execute(text("UPDATE ticker SET name=:n WHERE symbol=:s AND (name IS NULL OR name='')"), 
                                                {"n": comp_name, "s": symbol.upper()})
                                            await session.commit()
                                    except Exception:
                                        pass
                                    res = await session.execute(text("""
                                        SELECT pd.date, pd.open, pd.high, pd.low, pd.close, pd.volume
                                        FROM price_daily pd JOIN ticker t ON t.id=pd.ticker_id
                                        WHERE t.symbol=:sym ORDER BY pd.date ASC
                                    """), {"sym": symbol.upper()})
                                    rows = res.fetchall()
                        except Exception as av_err:
                            log.warning(f"Alpha Vantage fallback failed for {symbol}: {av_err}")
                    
                    # Try Finnhub candle data (2y history)
                    if not rows:
                        fk = os.getenv('FINNHUB_KEY') or os.getenv('FINNHUB_API_KEY')
                        if fk:
                            try:
                                import time
                                end = int(time.time())
                                start = end - 60*60*24*365
                                r = requests.get('https://finnhub.io/api/v1/stock/candle',
                                    params={'symbol':symbol.upper(),'resolution':'D','from':start,'to':end,'token':fk}, timeout=15)
                                j = r.json()
                                if j and j.get('s')=='ok':
                                    rows_to_insert = []
                                    for i, ts in enumerate(j['t']):
                                        d = datetime.fromtimestamp(ts).date()
                                        rows_to_insert.append({
                                            "date": d, 
                                            "open": float(j['o'][i]), 
                                            "high": float(j['h'][i]),
                                            "low": float(j['l'][i]), 
                                            "close": float(j['c'][i]),
                                            "volume": int(j['v'][i] or 0)
                                        })
                                    if rows_to_insert:
                                        await upsert_history_db(session, symbol, rows_to_insert)
                                        # Try to fetch company name/description from fundamentals service
                                        try:
                                            from app.services.fundamentals import fundamentals_service
                                            fund = await fundamentals_service.get_fundamentals(symbol.upper())
                                            comp_name = fund.get('longName') or fund.get('shortName')
                                            if comp_name:
                                                await session.execute(text("UPDATE ticker SET name=:n WHERE symbol=:s AND (name IS NULL OR name='')"), 
                                                    {"n": comp_name, "s": symbol.upper()})
                                                await session.commit()
                                        except Exception:
                                            pass
                                        res = await session.execute(text("""
                                            SELECT pd.date, pd.open, pd.high, pd.low, pd.close, pd.volume
                                            FROM price_daily pd JOIN ticker t ON t.id=pd.ticker_id
                                            WHERE t.symbol=:sym ORDER BY pd.date ASC
                                        """), {"sym": symbol.upper()})
                                        rows = res.fetchall()
                            except Exception as fh_err:
                                log.warning(f"Finnhub fallback failed for {symbol}: {fh_err}")
                except Exception as fallback_err:
                    log.error(f"All fallbacks failed for {symbol}: {fallback_err}")

        if rows and len(rows) > 0:
            ohlc = []
            from datetime import datetime as _dt
            for row in rows:
                if hasattr(row.date, 'timestamp'):
                    date_ms = int(row.date.timestamp() * 1000)
                else:
                    dt = _dt.combine(row.date, _dt.min.time())
                    date_ms = int(dt.timestamp() * 1000)
                ohlc.append([
                    date_ms,
                    float(row.open or 0),
                    float(row.high or 0),
                    float(row.low or 0),
                    float(row.close),
                    int(row.volume or 0)
                ])

            latest_close = float(rows[-1].close)
            prev_close = float(rows[-2].close) if len(rows) > 1 else latest_close

            from app.services.fundamentals import fundamentals_service
            fundamentals = await fundamentals_service.get_fundamentals(symbol.upper())

            # Fallback 52w hi/lo from DB
            all_highs = [float(row.high) for row in rows if row.high is not None]
            all_lows = [float(row.low) for row in rows if row.low is not None]
            if fundamentals.get("fiftyTwoWeekHigh") is None and all_highs:
                fundamentals["fiftyTwoWeekHigh"] = float(max(all_highs))
            if fundamentals.get("fiftyTwoWeekLow") is None and all_lows:
                fundamentals["fiftyTwoWeekLow"] = float(min(all_lows))

            return {
                "symbol": symbol.upper(),
                "latest": {"close": latest_close, "prevClose": prev_close},
                "ohlc": ohlc,
                "fundamentals": fundamentals,
            }
        else:
            log.error(f"No data found after all fallback attempts for {symbol}")
            raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found - all data sources failed")
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"/data error {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickers/{symbol}/intraday")
async def get_intraday(
    symbol: str,
    period_days: int = Query(default=7, ge=1, le=7),
    interval: str = Query(default="1m")
):
    """
    Get 1-minute intraday OHLCV candles for the last N days (max 7).
    
    Note: Free data sources (Yahoo Finance) typically limit intraday data to 5-7 days.
    Returns whatever data is available, which may be less than requested.
    """
    if interval != "1m":
        raise HTTPException(
            status_code=400, 
            detail="Only 1-minute interval ('1m') is currently supported"
        )
    
    try:
        from app.services.market_data import fetch_intraday_data
        
        result = await fetch_intraday_data(symbol.upper(), period_days)
        
        if result is None:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch intraday data for {symbol}. Provider may be unavailable or symbol invalid."
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Intraday data error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class _ImportPath(BaseModel):
    path: str

@router.post("/admin/import/names")
async def admin_import_names(body: _ImportPath):
    # call the seeder's helper directly (sync engine)
    from sqlalchemy import create_engine
    from dotenv import load_dotenv
    load_dotenv()
    try:
        from ...seed.seed_from_kaggle import upsert_names_csv, get_database_url
        engine = create_engine(get_database_url())
        count = upsert_names_csv(engine, body.path)
        return {"status": "ok", "updated": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/admin/import/prices")
async def admin_import_prices(body: _ImportPath):
    from sqlalchemy import create_engine
    from dotenv import load_dotenv
    load_dotenv()
    try:
        from ...seed.seed_from_kaggle import upsert_prices_csv, get_database_url
        engine = create_engine(get_database_url())
        count = upsert_prices_csv(engine, body.path)
        return {"status": "ok", "upserted": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/admin/import/names_dir")
async def admin_import_names_dir(body: _ImportPath):
    from sqlalchemy import create_engine
    from dotenv import load_dotenv
    load_dotenv()
    try:
        from ...seed.seed_from_kaggle import upsert_names_dir, get_database_url
        engine = create_engine(get_database_url())
        count = upsert_names_dir(engine, body.path)
        return {"status": "ok", "updated": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/admin/import/prices_dir")
async def admin_import_prices_dir(body: _ImportPath):
    from sqlalchemy import create_engine
    from dotenv import load_dotenv
    load_dotenv()
    try:
        from ...seed.seed_from_kaggle import upsert_prices_dir, get_database_url
        engine = create_engine(get_database_url())
        count = upsert_prices_dir(engine, body.path)
        return {"status": "ok", "upserted": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Watchlist and Portfolio endpoints are now in portfolios_watchlists.py