"""
Multiple data source handlers for stock market data.
Provides fallback mechanisms when primary sources fail.
"""
import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import logging
import pandas as pd
from decimal import Decimal

logger = logging.getLogger(__name__)


class DataSourceError(Exception):
    """Custom exception for data source errors."""
    pass


class StockDataFetcher:
    """Orchestrates multiple data sources with fallback logic."""
    
    def __init__(self):
        self.alphavantage_key = os.getenv('ALPHAVANTAGE_KEY')
        self.finnhub_key = os.getenv('FINNHUB_KEY')
        self.errors = []
    
    async def fetch_with_yfinance(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Primary method: yfinance with multiple retry strategies."""
        import yfinance as yf
        
        strategies = [
            {
                'name': 'Standard 5-year history',
                'params': {
                    'start': datetime.now() - timedelta(days=5*365),
                    'end': datetime.now(),
                    'interval': '1d'
                }
            },
            {
                'name': 'Period-based 5y with auto_adjust',
                'params': {
                    'period': '5y',
                    'interval': '1d',
                    'auto_adjust': True,
                    'prepost': False
                }
            },
            {
                'name': 'Last 1 year fallback',
                'params': {
                    'period': '1y',
                    'interval': '1d',
                    'auto_adjust': True,
                    'prepost': True
                }
            }
        ]
        
        for strategy in strategies:
            try:
                logger.info(f"  ↳ Trying yfinance: {strategy['name']}")
                ticker = yf.Ticker(symbol)
                
                # Fetch history
                hist = ticker.history(**strategy['params'])
                
                if hist.empty:
                    logger.warning(f"    Empty data for {symbol} with {strategy['name']}")
                    continue
                
                # Try to get fundamentals
                try:
                    info = ticker.info
                    name = info.get('longName', info.get('shortName', symbol))
                    exchange = info.get('exchange', 'UNKNOWN')
                    pe_ratio = info.get('trailingPE')
                    market_cap = info.get('marketCap')
                    avg_volume = info.get('averageVolume')
                except Exception as info_err:
                    logger.warning(f"    Fundamentals unavailable for {symbol}: {info_err}")
                    name = symbol
                    exchange = 'UNKNOWN'
                    pe_ratio = None
                    market_cap = None
                    avg_volume = None
                
                logger.info(f"    ✓ yfinance SUCCESS: {len(hist)} rows")
                return {
                    'symbol': symbol,
                    'name': name,
                    'exchange': exchange,
                    'history': hist,
                    'pe': pe_ratio,
                    'market_cap': market_cap,
                    'avg_volume': avg_volume,
                    'source': f'yfinance ({strategy["name"]})'
                }
                
            except Exception as e:
                error_msg = str(e)
                if 'no timezone' in error_msg.lower() or 'delisted' in error_msg.lower():
                    logger.warning(f"    Timezone/delisting error: {error_msg}")
                else:
                    logger.warning(f"    Error with {strategy['name']}: {error_msg}")
                self.errors.append({
                    'symbol': symbol,
                    'source': 'yfinance',
                    'strategy': strategy['name'],
                    'error': error_msg
                })
                continue
        
        return None
    
    async def fetch_with_yahooquery(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fallback 1: yahooquery library."""
        try:
            logger.info(f"  ↳ Trying yahooquery...")
            from yahooquery import Ticker
            
            ticker = Ticker(symbol)
            
            # Fetch historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5*365)
            
            hist = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if hist.empty or isinstance(hist, dict):
                logger.warning(f"    yahooquery returned empty/invalid data")
                return None
            
            # Get fundamentals
            try:
                info = ticker.summary_detail[symbol]
                profile = ticker.asset_profile.get(symbol, {})
                
                name = profile.get('longBusinessSummary', symbol)[:100] if profile else symbol
                exchange = profile.get('exchange', 'UNKNOWN') if profile else 'UNKNOWN'
                pe_ratio = info.get('trailingPE', {}).get('raw') if isinstance(info.get('trailingPE'), dict) else None
                market_cap = info.get('marketCap', {}).get('raw') if isinstance(info.get('marketCap'), dict) else None
                avg_volume = info.get('averageVolume', {}).get('raw') if isinstance(info.get('averageVolume'), dict) else None
            except Exception as info_err:
                logger.warning(f"    yahooquery fundamentals unavailable: {info_err}")
                name = symbol
                exchange = 'UNKNOWN'
                pe_ratio = None
                market_cap = None
                avg_volume = None
            
            # Convert to standard format
            if isinstance(hist.index, pd.MultiIndex):
                hist = hist.reset_index(level=0, drop=True)
            
            logger.info(f"    ✓ yahooquery SUCCESS: {len(hist)} rows")
            return {
                'symbol': symbol,
                'name': name,
                'exchange': exchange,
                'history': hist,
                'pe': pe_ratio,
                'market_cap': market_cap,
                'avg_volume': avg_volume,
                'source': 'yahooquery'
            }
            
        except ImportError:
            logger.info(f"    yahooquery not installed, skipping...")
            return None
        except Exception as e:
            logger.warning(f"    yahooquery error: {e}")
            self.errors.append({
                'symbol': symbol,
                'source': 'yahooquery',
                'error': str(e)
            })
            return None
    
    async def fetch_with_alphavantage(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fallback 2: AlphaVantage API."""
        if not self.alphavantage_key or self.alphavantage_key == 'your_alphavantage_key':
            return None
        
        try:
            logger.info(f"  ↳ Trying AlphaVantage...")
            from alpha_vantage.timeseries import TimeSeries
            
            ts = TimeSeries(key=self.alphavantage_key, output_format='pandas')
            data, meta_data = ts.get_daily(symbol=symbol, outputsize='full')
            
            if data.empty:
                logger.warning(f"    AlphaVantage returned empty data")
                return None
            
            # Rename columns to match our format
            data.columns = ['open', 'high', 'low', 'close', 'volume']
            data.index.name = 'date'
            
            # Filter to last 5 years
            five_years_ago = datetime.now() - timedelta(days=5*365)
            data = data[data.index >= five_years_ago]
            
            # Fundamentals not available from basic AlphaVantage endpoint
            logger.info(f"    ✓ AlphaVantage SUCCESS: {len(data)} rows")
            return {
                'symbol': symbol,
                'name': symbol,
                'exchange': 'UNKNOWN',
                'history': data,
                'pe': None,
                'market_cap': None,
                'avg_volume': None,
                'source': 'alphavantage'
            }
            
        except ImportError:
            logger.info(f"    alpha_vantage not installed, skipping...")
            return None
        except Exception as e:
            logger.warning(f"    AlphaVantage error: {e}")
            self.errors.append({
                'symbol': symbol,
                'source': 'alphavantage',
                'error': str(e)
            })
            return None
    
    async def fetch_with_finnhub(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fallback 3: Finnhub API."""
        if not self.finnhub_key or self.finnhub_key == 'your_finnhub_key':
            return None
        
        try:
            logger.info(f"  ↳ Trying Finnhub...")
            import finnhub
            
            finnhub_client = finnhub.Client(api_key=self.finnhub_key)
            
            # Fetch candles (daily data)
            end_date = int(datetime.now().timestamp())
            start_date = int((datetime.now() - timedelta(days=5*365)).timestamp())
            
            candles = finnhub_client.stock_candles(symbol, 'D', start_date, end_date)
            
            if candles.get('s') != 'ok' or not candles.get('c'):
                logger.warning(f"    Finnhub returned no data")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame({
                'open': candles['o'],
                'high': candles['h'],
                'low': candles['l'],
                'close': candles['c'],
                'volume': candles['v']
            })
            df['date'] = pd.to_datetime(candles['t'], unit='s')
            df.set_index('date', inplace=True)
            
            # Try to get company profile
            try:
                profile = finnhub_client.company_profile2(symbol=symbol)
                name = profile.get('name', symbol)
                exchange = profile.get('exchange', 'UNKNOWN')
                market_cap = profile.get('marketCapitalization', None)
                if market_cap:
                    market_cap = int(market_cap * 1_000_000)  # Convert from millions
            except:
                name = symbol
                exchange = 'UNKNOWN'
                market_cap = None
            
            logger.info(f"    ✓ Finnhub SUCCESS: {len(df)} rows")
            return {
                'symbol': symbol,
                'name': name,
                'exchange': exchange,
                'history': df,
                'pe': None,
                'market_cap': market_cap,
                'avg_volume': None,
                'source': 'finnhub'
            }
            
        except ImportError:
            logger.info(f"    finnhub-python not installed, skipping...")
            return None
        except Exception as e:
            logger.warning(f"    Finnhub error: {e}")
            self.errors.append({
                'symbol': symbol,
                'source': 'finnhub',
                'error': str(e)
            })
            return None
    
    async def fetch_stock_data(self, symbol: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Fetch stock data with comprehensive fallback logic.
        
        Returns:
            Tuple of (data_dict, has_partial_fundamentals)
        """
        logger.info(f"Fetching data for {symbol}...")
        
        # Try all sources in order
        sources = [
            self.fetch_with_yfinance,
            self.fetch_with_yahooquery,
            self.fetch_with_alphavantage,
            self.fetch_with_finnhub
        ]
        
        for fetch_func in sources:
            result = await fetch_func(symbol)
            if result:
                # Check if fundamentals are missing
                has_partial = (
                    result.get('pe') is None or 
                    result.get('market_cap') is None or 
                    result.get('avg_volume') is None
                )
                return result, has_partial
            
            # Rate limiting between attempts
            await asyncio.sleep(0.5)
        
        logger.error(f"❌ NO DATA SOURCES SUCCEEDED for {symbol}")
        self.errors.append({
            'symbol': symbol,
            'source': 'ALL',
            'error': 'All data sources failed'
        })
        return None, False

