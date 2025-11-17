"""
Market data service - REAL DATA ONLY, NO FAKE SHIT
"""
import asyncio
import aiohttp
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from datetime import date as _date, timedelta as _td, datetime as _dt
from sqlalchemy import text
import logging

log = logging.getLogger(__name__)

async def fetch_real_data_yahoo_api(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch REAL data from Yahoo Finance API"""
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                'range': '1y',
                'interval': '1d',
                'includePrePost': 'true',
                'events': 'div%2Csplit'
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'chart' in data and data['chart']['result']:
                        result = data['chart']['result'][0]
                        meta = result.get('meta', {})
                        timestamps = result.get('timestamp', [])
                        
                        if timestamps and result['indicators']['quote']:
                            quotes = result['indicators']['quote'][0]
                            
                            # Get latest data
                            closes = [c for c in quotes['close'] if c is not None]
                            if closes:
                                latest_close = closes[-1]
                                prev_close = closes[-2] if len(closes) > 1 else latest_close
                                
                                # Calculate 52-week high/low
                                highs = [h for h in quotes['high'] if h is not None]
                                lows = [l for l in quotes['low'] if l is not None]
                                
                                # Create OHLC data
                                ohlc = []
                                for i in range(len(timestamps)):
                                    if quotes['open'][i] is not None:
                                        ohlc.append([
                                            timestamps[i] * 1000,
                                            float(quotes['open'][i]),
                                            float(quotes['high'][i]),
                                            float(quotes['low'][i]),
                                            float(quotes['close'][i]),
                                            int(quotes['volume'][i] or 0)
                                        ])
                                
                                return {
                                    "symbol": symbol,
                                    "latest": {
                                        "close": float(latest_close),
                                        "prevClose": float(prev_close)
                                    },
                                    "ohlc": ohlc,
                                    "fundamentals": {
                                        "trailingPE": meta.get('trailingPE'),
                                        "marketCap": meta.get('marketCap'),
                                        "fiftyTwoWeekHigh": float(max(highs)) if highs else None,
                                        "fiftyTwoWeekLow": float(min(lows)) if lows else None,
                                        "beta": meta.get('beta'),
                                        "dividendYield": meta.get('dividendYield'),
                                    }
                                }
    except Exception as e:
        log.warning(f"Yahoo API failed for {symbol}: {e}")
    
    return None

async def fetch_real_data_yfinance(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch REAL data using yfinance library"""
    try:
        ticker = yf.Ticker(symbol)
        
        # Get historical data
        hist = ticker.history(period="1y", interval="1d")
        if hist is None or len(hist) == 0:
            return None
        
        # Get info (fundamentals)
        info = ticker.info or {}
        
        # Create OHLC data
        ohlc = []
        for idx, row in hist.iterrows():
            ohlc.append([
                int(idx.timestamp() * 1000),
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                int(row['Volume'])
            ])
        
        latest_close = float(hist['Close'].iloc[-1])
        prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else latest_close
        
        return {
            "symbol": symbol,
            "latest": {
                "close": latest_close,
                "prevClose": prev_close
            },
            "ohlc": ohlc,
            "fundamentals": {
                "trailingPE": info.get('trailingPE'),
                "marketCap": info.get('marketCap'),
                "fiftyTwoWeekHigh": info.get('fiftyTwoWeekHigh'),
                "fiftyTwoWeekLow": info.get('fiftyTwoWeekLow'),
                "beta": info.get('beta'),
                "dividendYield": info.get('dividendYield'),
            }
        }
    except Exception as e:
        log.warning(f"yfinance failed for {symbol}: {e}")
    
    return None

async def fetch_market_data(symbol: str, range_days: int = 365) -> Dict[str, Any]:
    """Fetch market data with multiple fallback sources - REAL DATA ONLY"""
    log.info(f"Fetching REAL market data for {symbol}")
    
    # Try Yahoo API first (most reliable)
    data = await fetch_real_data_yahoo_api(symbol)
    if data:
        log.info(f"Got REAL data from Yahoo API for {symbol}")
        return data
    
    # Try yfinance as fallback
    data = await fetch_real_data_yfinance(symbol)
    if data:
        log.info(f"Got REAL data from yfinance for {symbol}")
        return data
    
    # NO FAKE DATA - Return error if we can't get real data
    log.error(f"NO REAL DATA AVAILABLE for {symbol} - all sources failed")
    raise Exception(f"Unable to fetch real market data for {symbol}. Please check your internet connection and try again.")

class MarketDataFetcher:
    async def fetch(self, symbol: str, range_days: int = 365) -> Dict[str, Any]:
        return await fetch_market_data(symbol, range_days)

def get_market_data_fetcher() -> MarketDataFetcher:
    return MarketDataFetcher()

def _last_business_day(today: Optional[_date] = None) -> _date:
    today = today or _date.today()
    wd = today.weekday()
    if wd == 5: return today - _td(days=1)
    if wd == 6: return today - _td(days=2)
    return today

async def fetch_daily_history(symbol: str, days: int = 420) -> List[Dict[str, Any]]:
    """
    Return list of dicts [{date, open, high, low, close, volume}] for ~last 400-420 days.
    Try ALL available sources with comprehensive fallbacks:
    1. yahooquery (fastest, most reliable)
    2. yfinance (second best)
    3. yahoo_fin (web scraping fallback)
    4. AlphaVantage (if API key available)
    5. Finnhub (if API key available)
    6. Direct Yahoo Finance web scraping (last resort)
    """
    sym = symbol.upper()
    
    # Try yahooquery
    try:
        import yahooquery as yq
        df = yq.Ticker(sym).history(period='2y', interval='1d')
        if df is not None and not df.empty:
            if hasattr(df, 'reset_index'):
                df = df.reset_index()
            rows=[]
            for idx, r in df.iterrows():
                # Try to get date from index or column
                d = None
                if 'date' in df.columns:
                    d = r['date']
                elif isinstance(idx, tuple) and len(idx) > 1:
                    d = idx[1]  # Multi-index (symbol, date)
                elif hasattr(idx, 'date'):
                    d = idx
                
                if d is not None:
                    if isinstance(d, str): 
                        d = _dt.fromisoformat(d).date()
                    elif hasattr(d, 'date'):
                        d = d.date() if callable(d.date) else d
                    
                    if d:
                        rows.append({
                            "date": d, 
                            "open": float(r.get('open',0) or r.get('Open',0) or 0), 
                            "high": float(r.get('high',0) or r.get('High',0) or 0),
                            "low": float(r.get('low',0) or r.get('Low',0) or 0), 
                            "close": float(r.get('close',0) or r.get('Close',0) or 0),
                            "volume": int(r.get('volume',0) or r.get('Volume',0) or 0)
                        })
            if rows:
                rows.sort(key=lambda x:x["date"])
                rows = rows[-days:]
                log.info(f"✅ yahooquery succeeded for {sym} ({len(rows)} rows)")
                return rows
    except Exception as e:
        log.warning(f"yahooquery failed for {sym}: {e}")
    
    # Try yfinance
    try:
        t = yf.Ticker(sym)
        hist = t.history(period='2y', interval='1d', auto_adjust=False)
        if hist is not None and not hist.empty:
            rows=[]
            for idx, r in hist.iterrows():
                d = idx.date()
                rows.append({"date": d, "open": float(r.get('Open',0) or 0), "high": float(r.get('High',0) or 0),
                             "low": float(r.get('Low',0) or 0), "close": float(r.get('Close',0) or 0),
                             "volume": int(r.get('Volume',0) or 0)})
            rows = rows[-days:]
            log.info(f"✅ yfinance succeeded for {sym} ({len(rows)} rows)")
            return rows
    except Exception as e:
        log.warning(f"yfinance failed for {sym}: {e}")
    
    # Try yahoo_fin (web scraping)
    try:
        from yahoo_fin import stock_info as si
        # Get historical data
        df = si.get_data(sym, start_date=(_dt.now() - _td(days=730)).strftime('%Y-%m-%d'))
        if df is not None and not df.empty:
            rows=[]
            for idx, r in df.iterrows():
                d = idx.date() if hasattr(idx, 'date') else idx
                rows.append({
                    "date": d,
                    "open": float(r.get('open',0) or 0),
                    "high": float(r.get('high',0) or 0),
                    "low": float(r.get('low',0) or 0),
                    "close": float(r.get('close',0) or 0),
                    "volume": int(r.get('volume',0) or 0)
                })
            rows = rows[-days:]
            log.info(f"✅ yahoo_fin succeeded for {sym} ({len(rows)} rows)")
            return rows
    except Exception as e:
        log.warning(f"yahoo_fin failed for {sym}: {e}")
    
    # Try AlphaVantage (if key)
    try:
        import os, requests
        av = os.getenv("ALPHA_VANTAGE_KEY") or os.getenv("ALPHAVANTAGE_KEY")
        if av:
            r = requests.get('https://www.alphavantage.co/query',
                             params={'function':'TIME_SERIES_DAILY','symbol':sym,'apikey':av,'outputsize':'full'},
                             timeout=12)
            ts = (r.json() or {}).get('Time Series (Daily)',{})
            if ts:
                rows=[]
                for ds, pd in ts.items():
                    d = _dt.strptime(ds, "%Y-%m-%d").date()
                    rows.append({"date": d, "open": float(pd['1. open']), "high": float(pd['2. high']),
                                 "low": float(pd['3. low']), "close": float(pd['4. close']),
                                 "volume": int(pd.get('5. volume',0) or 0)})
                rows.sort(key=lambda x:x["date"])
                rows = rows[-days:]
                log.info(f"✅ AlphaVantage succeeded for {sym} ({len(rows)} rows)")
                return rows
    except Exception as e:
        log.warning(f"AlphaVantage failed for {sym}: {e}")
    
    # Try Finnhub (if key) — daily candles last ~2y
    try:
        import os, requests, time
        fk = os.getenv("FINNHUB_KEY") or os.getenv("FINNHUB_API_KEY")
        if fk:
            end = int(time.time())
            start = end - 60*60*24*730
            r = requests.get('https://finnhub.io/api/v1/stock/candle',
                             params={'symbol':sym,'resolution':'D','from':start,'to':end,'token':fk}, timeout=12)
            j = r.json()
            if j and j.get('s')=='ok':
                rows=[]
                for i, ts in enumerate(j['t']):
                    d = _dt.fromtimestamp(ts).date()
                    rows.append({"date": d, "open": float(j['o'][i]), "high": float(j['h'][i]),
                                 "low": float(j['l'][i]), "close": float(j['c'][i]),
                                 "volume": int(j['v'][i] or 0)})
                rows = rows[-days:]
                log.info(f"✅ Finnhub succeeded for {sym} ({len(rows)} rows)")
                return rows
    except Exception as e:
        log.warning(f"Finnhub failed for {sym}: {e}")
    
    # Last resort: Direct Yahoo Finance web scraping
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        
        # Try to get data from Yahoo Finance history page
        end_ts = int(_dt.now().timestamp())
        start_ts = int((_dt.now() - _td(days=730)).timestamp())
        url = f"https://query1.finance.yahoo.com/v7/finance/download/{sym}?period1={start_ts}&period2={end_ts}&interval=1d&events=history"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code == 200:
            import io
            df = pd.read_csv(io.StringIO(r.text))
            if df is not None and not df.empty:
                rows=[]
                for idx, row in df.iterrows():
                    try:
                        d = _dt.strptime(row['Date'], "%Y-%m-%d").date()
                        rows.append({
                            "date": d,
                            "open": float(row.get('Open', 0) or 0),
                            "high": float(row.get('High', 0) or 0),
                            "low": float(row.get('Low', 0) or 0),
                            "close": float(row.get('Close', 0) or 0),
                            "volume": int(row.get('Volume', 0) or 0)
                        })
                    except:
                        continue
                if rows:
                    rows = rows[-days:]
                    log.info(f"✅ Direct Yahoo web scraping succeeded for {sym} ({len(rows)} rows)")
                    return rows
    except Exception as e:
        log.warning(f"Direct Yahoo web scraping failed for {sym}: {e}")
    
    # All sources failed
    log.error(f"❌ ALL {sym} data sources failed (yahooquery, yfinance, yahoo_fin, AlphaVantage, Finnhub, web scraping)")
    raise RuntimeError(f"No provider returned data for {sym} after trying all fallbacks")

async def upsert_history_db(session, symbol: str, rows: List[Dict[str, Any]]) -> int:
    """UPSERT recent rows for one symbol into price_daily."""
    sym = symbol.upper()
    tid = (await session.execute(text("SELECT id FROM ticker WHERE symbol=:s"), {"s": sym})).scalar()
    if tid is None:
        await session.execute(text("INSERT INTO ticker(symbol) VALUES (:s)"), {"s": sym})
        tid = (await session.execute(text("SELECT id FROM ticker WHERE symbol=:s"), {"s": sym})).scalar()
    inserted=0
    for r in rows:
        await session.execute(text("""
            INSERT INTO price_daily(ticker_id,date,open,high,low,close,volume)
            VALUES (:tid,:d,:o,:h,:l,:c,:v)
            ON CONFLICT (ticker_id,date) DO UPDATE
            SET open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                close=EXCLUDED.close, volume=EXCLUDED.volume
        """), {"tid":tid, "d":r["date"], "o":r["open"], "h":r["high"], "l":r["low"], "c":r["close"], "v":r["volume"]})
        inserted += 1
    await session.commit()
    return inserted