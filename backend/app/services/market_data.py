"""
Market data service - REAL DATA ONLY, NO FAKE SHIT
"""
import asyncio
import aiohttp
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
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