"""
Fundamentals data fetching service with Alpha Vantage and Finnhub APIs.
Designed to work in real-time when ticker detail pages are loaded.
"""
import asyncio
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

log = logging.getLogger(__name__)

class FundamentalsService:
    """Service for fetching fundamentals data with Alpha Vantage and Finnhub APIs."""
    
    def __init__(self):
        self.cache = {}  # Simple in-memory cache for 5 minutes
        self.cache_duration = 300  # 5 minutes
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_KEY') or os.getenv('ALPHAVANTAGE_KEY')
        self.finnhub_key = os.getenv('FINNHUB_KEY') or os.getenv('FINNHUB_API_KEY')
        
        log.info(f"API Keys Status - Alpha Vantage: {'✓' if self.alpha_vantage_key else '✗'}, Finnhub: {'✓' if self.finnhub_key else '✗'}")
    
    async def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch fundamentals for a symbol using yahooquery (preferred), Finnhub, and Alpha Vantage APIs.
        Uses 5-minute cache if data already available.
        Returns a dictionary with P/E ratio, Market Cap, Beta, and company name.
        """
        symbol = symbol.upper()
        
        # Check cache first
        cache_key = f"fundamentals_{symbol}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_duration:
                log.info(f"Using cached fundamentals for {symbol}")
                return cached_data
        
        log.info(f"🔄 Fetching fresh fundamentals for {symbol}")
        
        # Try APIs in order of preference (yahooquery first for free name + fundamentals)
        apis = [
            ("yahooquery", self._fetch_yahooquery),
            ("finnhub", self._fetch_finnhub),
            ("alpha_vantage", self._fetch_alpha_vantage),
            ("calculated", self._fetch_calculated),
        ]
        
        for api_name, fetch_func in apis:
            try:
                log.info(f"Trying {api_name} for {symbol}")
                result = await fetch_func(symbol)
                if result and self._is_valid_fundamentals(result):
                    # Cache the result
                    self.cache[cache_key] = (result, datetime.now())
                    log.info(f"✅ Successfully fetched fundamentals for {symbol} using {api_name}")
                    
                    # Store company name in database if available
                    if result.get('longName') or result.get('shortName'):
                        await self._store_company_name(symbol, result)
                    
                    return result
            except Exception as e:
                log.warning(f"{api_name} failed for {symbol}: {e}")
                continue
        
        # If all APIs fail, return empty fundamentals
        log.warning(f"⚠️ All fundamentals APIs failed for {symbol}")
        return self._empty_fundamentals()
    
    async def _fetch_yahooquery(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch fundamentals using yahooquery (free, no API key needed)."""
        try:
            import yahooquery as yq
            import asyncio
            
            log.info(f"Fetching yahooquery data for {symbol}")
            
            # Run in thread to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _fetch_sync():
                ticker = yq.Ticker(symbol)
                
                # Get company name from price module
                price_data = ticker.price
                name = None
                if isinstance(price_data, dict) and symbol in price_data:
                    name = price_data[symbol].get('longName') or price_data[symbol].get('shortName')
                
                # Get fundamentals from summary_detail
                summary = ticker.summary_detail
                key_stats = ticker.key_stats
                
                result = {
                    'price': price_data.get(symbol, {}),
                    'summary': summary.get(symbol, {}) if isinstance(summary, dict) else {},
                    'stats': key_stats.get(symbol, {}) if isinstance(key_stats, dict) else {},
                    'name': name
                }
                
                return result
            
            data = await loop.run_in_executor(None, _fetch_sync)
            
            if not data.get('name'):
                log.warning(f"yahooquery returned no company name for {symbol}")
                # Still try to get fundamentals even without name
            
            price = data.get('price', {})
            summary = data.get('summary', {})
            stats = data.get('stats', {})
            
            # Extract fundamentals
            pe_ratio = summary.get('trailingPE') or price.get('trailingPE')
            market_cap = price.get('marketCap')
            beta = summary.get('beta')
            dividend_yield = summary.get('dividendYield')
            week_52_high = summary.get('fiftyTwoWeekHigh')
            week_52_low = summary.get('fiftyTwoWeekLow')
            
            fundamentals = {
                "trailingPE": float(pe_ratio) if pe_ratio else None,
                "marketCap": int(float(market_cap)) if market_cap else None,
                "fiftyTwoWeekHigh": float(week_52_high) if week_52_high else None,
                "fiftyTwoWeekLow": float(week_52_low) if week_52_low else None,
                "beta": float(beta) if beta else None,
                "dividendYield": float(dividend_yield) if dividend_yield else None,
                "avgVolume": None,
                "longName": data.get('name'),
                "shortName": data.get('name'),  # yahooquery doesn't distinguish, use same
                "source": "yahooquery"
            }
            
            log.info(f"yahooquery fundamentals for {symbol}: Name={data.get('name')}, PE={pe_ratio}, MC={market_cap}")
            return fundamentals
            
        except Exception as e:
            log.error(f"yahooquery error for {symbol}: {e}")
            return None
    
    async def _fetch_finnhub(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch fundamentals using Finnhub API (with requests for reliability)."""
        if not self.finnhub_key:
            log.info("Finnhub API key not available")
            return None
            
        try:
            import requests
            import asyncio
            
            log.info(f"Fetching Finnhub data for {symbol}")
            
            # Run in thread to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _fetch_sync():
                base_url = "https://finnhub.io/api/v1"
                headers = {"X-Finnhub-Token": self.finnhub_key}
                
                # Get company profile for market cap and name
                profile_url = f"{base_url}/stock/profile2"
                profile_resp = requests.get(profile_url, params={"symbol": symbol}, headers=headers, timeout=10)
                profile = profile_resp.json() if profile_resp.status_code == 200 else {}
                
                # Get basic financials for P/E, beta, etc.
                financials_url = f"{base_url}/stock/metric"
                financials_resp = requests.get(financials_url, params={"symbol": symbol, "metric": "all"}, headers=headers, timeout=10)
                financials = financials_resp.json() if financials_resp.status_code == 200 else {}
                
                return {
                    'profile': profile,
                    'financials': financials
                }
            
            data = await loop.run_in_executor(None, _fetch_sync)
            
            profile = data.get('profile', {})
            financials = data.get('financials', {})
            
            if not profile or not profile.get('name'):
                log.warning(f"Finnhub returned empty profile for {symbol}")
                return None
            
            log.info(f"Finnhub profile for {symbol}: {profile.get('name')}")
            
            # Extract fundamentals from metrics
            metrics = financials.get('metric', {})
            
            # Market Cap (from profile, in millions)
            market_cap = profile.get('marketCapitalization')
            if market_cap:
                market_cap = int(float(market_cap) * 1_000_000)  # Convert from millions
            
            # P/E Ratio (from metrics)
            pe_ratio = metrics.get('peBasicExclExtraTTM') or metrics.get('peExclExtraAnnual')
            if pe_ratio:
                pe_ratio = float(pe_ratio)
            
            # Beta (from metrics)
            beta = metrics.get('beta')
            if beta:
                beta = float(beta)
            
            # Dividend Yield (from metrics)
            dividend_yield = metrics.get('dividendYieldIndicatedAnnual')
            if dividend_yield:
                dividend_yield = float(dividend_yield)
            
            # 52-week high/low (from metrics)
            week_52_high = metrics.get('52WeekHigh')
            week_52_low = metrics.get('52WeekLow')
            
            fundamentals = {
                "trailingPE": pe_ratio,
                "marketCap": market_cap,
                "fiftyTwoWeekHigh": float(week_52_high) if week_52_high else None,
                "fiftyTwoWeekLow": float(week_52_low) if week_52_low else None,
                "beta": beta,
                "dividendYield": dividend_yield,
                "avgVolume": None,  # Will calculate from price data
                "longName": profile.get('name'),  # Store company name
                "source": "finnhub"
            }
            
            log.info(f"Finnhub fundamentals for {symbol}: PE={pe_ratio}, MC={market_cap}, Beta={beta}")
            return fundamentals
            
        except Exception as e:
            log.error(f"Finnhub error for {symbol}: {e}")
            return None
    
    async def _fetch_alpha_vantage(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch fundamentals using Alpha Vantage API."""
        if not self.alpha_vantage_key:
            log.info(f"Alpha Vantage key not set for {symbol}")
            return None
            
        try:
            import requests
            import asyncio
            
            log.info(f"Fetching Alpha Vantage data for {symbol}")
            
            # Run in thread to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _fetch_sync():
                # Get company overview (includes P/E, market cap, beta)
                url = f"https://www.alphavantage.co/query"
                params = {
                    'function': 'OVERVIEW',
                    'symbol': symbol,
                    'apikey': self.alpha_vantage_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'Error Message' in data or 'Note' in data:
                    log.warning(f"Alpha Vantage error message for {symbol}: {data}")
                    return None
                
                return data
            
            data = await loop.run_in_executor(None, _fetch_sync)
            
            if not data:
                log.warning(f"Alpha Vantage returned no data for {symbol}")
                return None
            
            log.info(f"Alpha Vantage raw data for {symbol}: {data.get('PERatio')}, {data.get('MarketCapitalization')}, {data.get('Beta')}")
            
            # Extract fundamentals
            pe_ratio = self._safe_float(data.get('PERatio'))
            market_cap = self._safe_int(data.get('MarketCapitalization'))
            beta = self._safe_float(data.get('Beta'))
            dividend_yield = self._safe_float(data.get('DividendYield'))
            
            fundamentals = {
                "trailingPE": pe_ratio,
                "marketCap": market_cap,
                "fiftyTwoWeekHigh": None,  # Will calculate from price data
                "fiftyTwoWeekLow": None,   # Will calculate from price data
                "beta": beta,
                "dividendYield": dividend_yield,
                "avgVolume": None,
                "longName": data.get('Name'),  # Alpha Vantage returns 'Name' field
                "source": "alpha_vantage"
            }
            
            log.info(f"Alpha Vantage fundamentals for {symbol}: {fundamentals}")
            return fundamentals
            
        except Exception as e:
            log.error(f"Alpha Vantage error for {symbol}: {e}")
            return None
    
    async def _fetch_calculated(self, symbol: str) -> Dict[str, Any]:
        """Calculate basic fundamentals from price data in database."""
        try:
            from app.db import SessionLocal
            from sqlalchemy import text
            
            async with SessionLocal() as session:
                # Get price data to calculate 52-week high/low and average volume
                result = await session.execute(text("""
                    SELECT 
                        MAX(high) as week_52_high,
                        MIN(low) as week_52_low,
                        AVG(volume) as avg_volume,
                        COUNT(*) as data_points
                    FROM price_daily pd
                    JOIN ticker t ON pd.ticker_id = t.id
                    WHERE t.symbol = :symbol
                    AND date >= CURRENT_DATE - INTERVAL '365 days'
                """), {"symbol": symbol.upper()})
                
                row = result.first()
                if row and row.data_points > 0:
                    return {
                        "trailingPE": None,  # Would need earnings data
                        "marketCap": None,   # Would need shares outstanding
                        "fiftyTwoWeekHigh": float(row.week_52_high) if row.week_52_high else None,
                        "fiftyTwoWeekLow": float(row.week_52_low) if row.week_52_low else None,
                        "beta": None,        # Would need correlation with market
                        "dividendYield": None,  # Would need dividend data
                        "avgVolume": int(float(row.avg_volume)) if row.avg_volume else None,
                        "source": "calculated"
                    }
        except Exception as e:
            log.warning(f"Calculated fundamentals failed for {symbol}: {e}")
        
        # Fallback to empty structure
        return {
            "trailingPE": None,
            "marketCap": None,
            "fiftyTwoWeekHigh": None,
            "fiftyTwoWeekLow": None,
            "beta": None,
            "dividendYield": None,
            "avgVolume": None,
            "source": "calculated"
        }
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == 'N/A' or value == '-':
            return None
        try:
            if isinstance(value, str):
                # Handle percentage values like "2.5%"
                if value.endswith('%'):
                    return float(value[:-1])
                # Handle values like "1.2M", "3.4B"
                if value.endswith('M'):
                    return float(value[:-1]) * 1_000_000
                if value.endswith('B'):
                    return float(value[:-1]) * 1_000_000_000
                if value.endswith('K'):
                    return float(value[:-1]) * 1_000
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to int."""
        if value is None or value == 'N/A' or value == '-':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _safe_market_cap(self, value) -> Optional[int]:
        """Safely convert market cap string to int."""
        if not value or value == 'N/A' or value == '-':
            return None
        
        try:
            value = str(value).upper()
            if value.endswith('T'):  # Trillion
                return int(float(value[:-1]) * 1_000_000_000_000)
            elif value.endswith('B'):  # Billion
                return int(float(value[:-1]) * 1_000_000_000)
            elif value.endswith('M'):  # Million
                return int(float(value[:-1]) * 1_000_000)
            elif value.endswith('K'):  # Thousand
                return int(float(value[:-1]) * 1_000)
            else:
                return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _is_valid_fundamentals(self, fundamentals: Dict[str, Any]) -> bool:
        """Check if fundamentals data is valid (has at least one meaningful value)."""
        # Consider it valid if we have at least one non-None value from the key fields
        key_fields = ["trailingPE", "marketCap", "beta", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "avgVolume"]
        return any(v is not None for field, v in fundamentals.items() if field in key_fields)
    
    def _empty_fundamentals(self) -> Dict[str, Any]:
        """Return empty fundamentals structure."""
        return {
            "trailingPE": None,
            "marketCap": None,
            "fiftyTwoWeekHigh": None,
            "fiftyTwoWeekLow": None,
            "beta": None,
            "dividendYield": None,
            "avgVolume": None,
            "longName": None,
            "shortName": None,
            "source": "none"
        }
    
    async def _store_company_name(self, symbol: str, fundamentals: Dict[str, Any]):
        """Store company name in the ticker table if not already present."""
        try:
            from app.db import SessionLocal
            from sqlalchemy import text
            
            name = fundamentals.get('longName') or fundamentals.get('shortName')
            if not name:
                return
            
            async with SessionLocal() as session:
                # Check if ticker exists and if name is missing
                result = await session.execute(text("""
                    SELECT id, name FROM ticker WHERE symbol = :symbol
                """), {"symbol": symbol})
                
                row = result.first()
                
                if row and (not row.name or row.name.strip() == ''):
                    # Update the name
                    await session.execute(text("""
                        UPDATE ticker SET name = :name WHERE symbol = :symbol
                    """), {"name": name, "symbol": symbol})
                    await session.commit()
                    log.info(f"✅ Stored company name '{name}' for {symbol} in database")
                elif not row:
                    # Create the ticker with name
                    await session.execute(text("""
                        INSERT INTO ticker (symbol, name) VALUES (:symbol, :name)
                        ON CONFLICT (symbol) DO UPDATE SET name = EXCLUDED.name
                    """), {"symbol": symbol, "name": name})
                    await session.commit()
                    log.info(f"✅ Created ticker {symbol} with name '{name}' in database")
                else:
                    log.debug(f"Ticker {symbol} already has name: {row.name}")
                    
        except Exception as e:
            log.warning(f"Failed to store company name for {symbol}: {e}")

# Global instance
fundamentals_service = FundamentalsService()
