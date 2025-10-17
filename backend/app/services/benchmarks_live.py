"""
Benchmarks Live Data Service
Fetches SPY, QQQ, DIA with last business day prices using yahoo_fin
"""
from yahoo_fin import stock_info as si
from datetime import datetime
from typing import Dict, List, Optional
import logging
from functools import lru_cache
import time

log = logging.getLogger(__name__)

# Simple in-memory cache with timestamp
_cache: Dict[str, tuple[float, dict]] = {}
CACHE_TTL_SECONDS = 60  # 60 seconds cache

def get_last_business_day_prices(symbol: str) -> Optional[Dict]:
    """
    Get last business day price data for a symbol.
    
    Returns:
        dict with: symbol, last_business_day, close, previous_close, change, change_pct
        None if fetch fails
    """
    try:
        # Get recent data (yahoo_fin returns most recent first by default)
        df = si.get_data(symbol, interval="1d", start_date=None, end_date=None)
        
        if df is None or df.empty or len(df) < 2:
            log.warning(f"Insufficient data for {symbol}: {len(df) if df is not None else 0} rows")
            return None
        
        # Get last two dates (most recent first in yahoo_fin)
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        last_date = last_row.name.date() if hasattr(last_row.name, 'date') else last_row.name
        close = float(last_row["close"])
        prev_close = float(prev_row["close"])
        
        change = close - prev_close
        change_pct = (change / prev_close * 100) if prev_close != 0 else 0.0
        
        return {
            "symbol": symbol,
            "last_business_day": last_date.isoformat() if hasattr(last_date, 'isoformat') else str(last_date),
            "close": round(close, 2),
            "previous_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
        }
    except Exception as e:
        log.exception(f"Failed to fetch {symbol} from yahoo_fin: {e}")
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
    - Full data: symbol, last_business_day, close, previous_close, change, change_pct
    - Error: symbol, error
    """
    symbols = ["SPY", "QQQ", "DIA"]
    results = []
    
    for symbol in symbols:
        try:
            data = get_cached_or_fetch(symbol)
            results.append(data)
        except Exception as e:
            log.exception(f"Unexpected error fetching {symbol}: {e}")
            results.append({
                "symbol": symbol,
                "error": f"Unexpected error: {str(e)}"
            })
    
    return results

