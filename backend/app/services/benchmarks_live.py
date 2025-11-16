"""
Benchmarks Live Data Service
Fetches SPY, QQQ, DIA with last business day prices using Alpha Vantage and Finnhub APIs
"""
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
import logging
import time

log = logging.getLogger(__name__)

# Simple in-memory cache with timestamp
_cache: Dict[str, tuple[float, dict]] = {}
CACHE_TTL_SECONDS = 60  # 60 seconds cache

def get_last_business_day_prices_alpha_vantage(symbol: str) -> Optional[Dict]:
    """
    Get last business day price data using Alpha Vantage API.
    
    Returns:
        dict with: symbol, last_business_day, close, previous_close, change, change_pct
        None if fetch fails
    """
    api_key = os.getenv('ALPHA_VANTAGE_KEY') or os.getenv('ALPHAVANTAGE_KEY')
    if not api_key:
        log.warning("Alpha Vantage API key not set")
        return None
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'apikey': api_key,
            'outputsize': 'compact'  # Last 100 days
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'Error Message' in data or 'Note' in data:
            log.warning(f"Alpha Vantage error for {symbol}: {data}")
            return None
        
        time_series = data.get('Time Series (Daily)', {})
        if not time_series or len(time_series) < 2:
            log.warning(f"Insufficient data for {symbol}: {len(time_series)} days")
            return None
        
        # Get last two dates (sorted)
        dates = sorted(time_series.keys(), reverse=True)
        last_date = dates[0]
        prev_date = dates[1]
        
        last_data = time_series[last_date]
        prev_data = time_series[prev_date]
        
        close = float(last_data['4. close'])
        prev_close = float(prev_data['4. close'])
        
        change = close - prev_close
        change_pct = (change / prev_close * 100) if prev_close != 0 else 0.0
        
        # Calculate 52-week high/low from available data (up to 100 days)
        all_highs = [float(time_series[date]['2. high']) for date in time_series.keys()]
        all_lows = [float(time_series[date]['3. low']) for date in time_series.keys()]
        week_52_high = max(all_highs) if all_highs else None
        week_52_low = min(all_lows) if all_lows else None
        
        return {
            "symbol": symbol,
            "last_business_day": last_date,
            "close": round(close, 2),
            "previous_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "week_52_high": round(week_52_high, 2) if week_52_high else None,
            "week_52_low": round(week_52_low, 2) if week_52_low else None,
        }
    except Exception as e:
        log.error(f"Failed to fetch {symbol} from Alpha Vantage: {e}")
        return None

def get_last_business_day_prices_finnhub(symbol: str) -> Optional[Dict]:
    """
    Get last business day price data using Finnhub API.
    
    Returns:
        dict with: symbol, last_business_day, close, previous_close, change, change_pct, week_52_high, week_52_low
        None if fetch fails
    """
    api_key = os.getenv('FINNHUB_KEY') or os.getenv('FINNHUB_API_KEY')
    if not api_key:
        log.warning("Finnhub API key not set")
        return None
    
    try:
        # Get quote (current price)
        quote_url = f"https://finnhub.io/api/v1/quote"
        params = {
            'symbol': symbol,
            'token': api_key
        }
        
        response = requests.get(quote_url, params=params, timeout=10)
        response.raise_for_status()
        quote = response.json()
        
        if not quote or 'c' not in quote:
            log.warning(f"No quote data for {symbol}")
            return None
        
        close = float(quote['c'])  # Current price
        prev_close = float(quote['pc'])  # Previous close
        
        change = close - prev_close
        change_pct = float(quote['dp'])  # Change percent
        
        # Get last business day (use today's date for now)
        last_date = datetime.now().strftime('%Y-%m-%d')
        
        # Fetch 52-week high/low from metrics endpoint
        week_52_high = None
        week_52_low = None
        try:
            metrics_url = f"https://finnhub.io/api/v1/stock/metric"
            metrics_params = {
                'symbol': symbol,
                'metric': 'all',
                'token': api_key
            }
            metrics_response = requests.get(metrics_url, params=metrics_params, timeout=10)
            metrics_response.raise_for_status()
            metrics = metrics_response.json()
            
            if metrics and 'metric' in metrics:
                week_52_high = metrics['metric'].get('52WeekHigh')
                week_52_low = metrics['metric'].get('52WeekLow')
        except Exception as e:
            log.warning(f"Failed to fetch 52-week data for {symbol}: {e}")
        
        return {
            "symbol": symbol,
            "last_business_day": last_date,
            "close": round(close, 2),
            "previous_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "week_52_high": round(week_52_high, 2) if week_52_high else None,
            "week_52_low": round(week_52_low, 2) if week_52_low else None,
        }
    except Exception as e:
        log.error(f"Failed to fetch {symbol} from Finnhub: {e}")
        return None

async def get_52_week_high_low_from_db(symbol: str) -> Optional[Dict]:
    """
    Get 52-week high/low from database for benchmarks.
    """
    try:
        from app.db import SessionLocal
        from sqlalchemy import text
        
        async with SessionLocal() as session:
            result = await session.execute(text("""
                SELECT 
                    MAX(high) as week_52_high,
                    MIN(low) as week_52_low
                FROM price_daily pd
                JOIN ticker t ON pd.ticker_id = t.id
                WHERE t.symbol = :symbol
                AND date >= CURRENT_DATE - INTERVAL '365 days'
            """), {"symbol": symbol.upper()})
            
            row = result.first()
            if row and row.week_52_high:
                return {
                    "week_52_high": round(float(row.week_52_high), 2),
                    "week_52_low": round(float(row.week_52_low), 2)
                }
    except Exception as e:
        log.error(f"Failed to fetch 52-week data from DB for {symbol}: {e}")
    
    return None

def get_last_business_day_prices(symbol: str) -> Optional[Dict]:
    """
    Get last business day price data with fallback between APIs.
    
    Returns:
        dict with: symbol, last_business_day, close, previous_close, change, change_pct, week_52_high, week_52_low
        None if all APIs fail
    """
    # Try Finnhub first (faster, more real-time)
    result = get_last_business_day_prices_finnhub(symbol)
    if result:
        return result
    
    # Fallback to Alpha Vantage
    result = get_last_business_day_prices_alpha_vantage(symbol)
    if result:
        return result
    
    return None


def get_cached_or_fetch(symbol: str) -> Dict:
    """
    Get benchmark data with 60-second in-memory cache.
    
    Returns:
        dict with data or error field
    """
    now = time.time()
    
    # Check cache
    if symbol in _cache:
        timestamp, data = _cache[symbol]
        if now - timestamp < CACHE_TTL_SECONDS:
            log.debug(f"Cache HIT for {symbol} (age: {now - timestamp:.1f}s)")
            return data
        else:
            log.debug(f"Cache EXPIRED for {symbol} (age: {now - timestamp:.1f}s)")
    
    # Fetch fresh data
    log.info(f"Fetching live data for {symbol}")
    data = get_last_business_day_prices(symbol)
    
    if data is None:
        # Return error object but still with symbol
        result = {
            "symbol": symbol,
            "error": f"Failed to fetch data for {symbol}"
        }
    else:
        result = data
    
    # Cache the result (even errors, to avoid hammering API)
    _cache[symbol] = (now, result)
    
    return result


async def get_all_benchmarks() -> List[Dict]:
    """
    Get all benchmark data (SPY, QQQ, DIA) with partial success support.
    
    Returns list of dicts, each with either:
    - Full data: symbol, last_business_day, close, previous_close, change, change_pct, week_52_high, week_52_low
    - Error: symbol, error
    """
    symbols = ["SPY", "QQQ", "DIA"]
    results = []
    
    for symbol in symbols:
        try:
            data = get_cached_or_fetch(symbol)
            
            # If 52-week data is missing, fetch from database
            if not data.get("error") and (not data.get("week_52_high") or not data.get("week_52_low")):
                db_data = await get_52_week_high_low_from_db(symbol)
                if db_data:
                    data["week_52_high"] = db_data["week_52_high"]
                    data["week_52_low"] = db_data["week_52_low"]
            
            results.append(data)
        except Exception as e:
            log.exception(f"Unexpected error fetching {symbol}: {e}")
            results.append({
                "symbol": symbol,
                "error": f"Unexpected error: {str(e)}"
            })
    
    return results

