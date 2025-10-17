"""
API routes for tickers, prices, and risk-free rates.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime
from typing import Optional, List
import logging

from app.db import get_session
from app.models import Ticker, PriceDaily, RiskFreeSeries, Watchlist, Portfolio, PortfolioHolding
from app.services.loader import load_sample_data
from app.services.market_data import get_market_data_fetcher
from app.services import watchlist_service, portfolio_service
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request validation
class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    inception_date: date
    initial_value: float = Field(default=0, ge=0)
    description: Optional[str] = Field(None, max_length=1000)
    
    @validator('inception_date')
    def validate_inception_date(cls, v):
        if v > date.today():
            raise ValueError('Inception date cannot be in the future')
        return v

class HoldingAdd(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)
    shares: float = Field(..., gt=0)
    average_cost: Optional[float] = Field(None, ge=0)


@router.get("/tickers")
async def get_tickers(
    search: Optional[str] = Query(None, description="Search by symbol or name"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    List or search tickers.
    
    - **search**: Optional search term for symbol or name
    - **limit**: Maximum number of results (default 100)
    - **offset**: Number of results to skip (default 0)
    """
    async with get_session() as session:
        try:
            query = select(Ticker)
            
            if search:
                search_pattern = f"%{search}%"
                query = query.where(
                    (Ticker.symbol.ilike(search_pattern)) | 
                    (Ticker.name.ilike(search_pattern))
                )
            
            query = query.order_by(Ticker.symbol).limit(limit).offset(offset)
            
            result = await session.execute(query)
            tickers = result.scalars().all()
            
            return {
                "count": len(tickers),
                "limit": limit,
                "offset": offset,
                "tickers": [
                    {
                        "id": str(ticker.id),
                        "symbol": ticker.symbol,
                        "name": ticker.name,
                        "exchange": ticker.exchange,
                        "created_at": ticker.created_at.isoformat()
                    }
                    for ticker in tickers
                ]
            }
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices/{symbol}")
async def get_prices(
    symbol: str,
    start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[date] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get daily OHLCV and fundamentals for a ticker symbol.
    
    - **symbol**: Ticker symbol (e.g., AAPL)
    - **start**: Optional start date
    - **end**: Optional end date
    """
    async with get_session() as session:
        try:
            # Find ticker
            result = await session.execute(
                select(Ticker).where(Ticker.symbol == symbol.upper())
            )
            ticker = result.scalar_one_or_none()
            
            if not ticker:
                raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")
            
            # Build price query
            query = select(PriceDaily).where(PriceDaily.ticker_id == ticker.id)
            
            if start:
                query = query.where(PriceDaily.date >= start)
            if end:
                query = query.where(PriceDaily.date <= end)
            
            query = query.order_by(PriceDaily.date)
            
            result = await session.execute(query)
            prices = result.scalars().all()
            
            return {
                "symbol": ticker.symbol,
                "name": ticker.name,
                "exchange": ticker.exchange,
                "count": len(prices),
                "prices": [
                    {
                        "date": price.date.isoformat(),
                        "open": float(price.open) if price.open else None,
                        "high": float(price.high) if price.high else None,
                        "low": float(price.low) if price.low else None,
                        "close": float(price.close),
                        "volume": price.volume,
                        "avg_volume": price.avg_volume,
                        "pe": float(price.pe) if price.pe else None,
                        "market_cap": price.market_cap
                    }
                    for price in prices
                ]
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching prices for {symbol}: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/riskfree")
async def get_risk_free_rates(
    start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    latest: bool = Query(False, description="Return only the latest rate")
):
    """
    Get risk-free rate data (3-month T-Bill).
    
    - **start**: Optional start date
    - **end**: Optional end date
    - **latest**: If true, return only the most recent rate
    """
    async with get_session() as session:
        try:
            if latest:
                query = select(RiskFreeSeries).order_by(RiskFreeSeries.date.desc()).limit(1)
            else:
                query = select(RiskFreeSeries)
                
                if start:
                    query = query.where(RiskFreeSeries.date >= start)
                if end:
                    query = query.where(RiskFreeSeries.date <= end)
                
                query = query.order_by(RiskFreeSeries.date)
            
            result = await session.execute(query)
            rates = result.scalars().all()
            
            if not rates:
                raise HTTPException(status_code=404, detail="No risk-free rate data found")
            
            return {
                "count": len(rates),
                "rates": [
                    {
                        "date": rate.date.isoformat(),
                        "rate": float(rate.rate)
                    }
                    for rate in rates
                ]
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching risk-free rates: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_data(
    symbols: Optional[List[str]] = Query(None, description="Symbols to refresh (default: top 5)")
):
    """
    Refresh data for specified symbols.
    
    - **symbols**: Optional list of symbols to refresh
    """
    try:
        stats = await load_sample_data(symbols)
        return {
            "message": "Data refresh complete",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error refreshing data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{symbol}")
async def get_market_data(
    symbol: str,
    range_days: int = Query(365, description="Number of days of historical data")
):
    """
    Fetch real-time market data (OHLCV + fundamentals) for a ticker.
    Uses multi-source fallback: Finnhub → AlphaVantage → YahooQuery
    
    - **symbol**: Ticker symbol (e.g., AAPL)
    - **range_days**: Number of days of historical data (default 365)
    """
    try:
        fetcher = get_market_data_fetcher()
        
        # Fetch price data
        price_data = await fetcher.get_price_data(symbol.upper(), range_days)
        
        if not price_data:
            raise HTTPException(
                status_code=404, 
                detail=f"No price data available for {symbol} from any source"
            )
        
        # Fetch fundamentals (only for currently viewed ticker)
        fundamentals = await fetcher.get_fundamentals(symbol.upper())
        
        response = {
            **price_data,
            'fundamentals': fundamentals if fundamentals else {
                'pe_ratio': None,
                'market_cap': None,
                'beta': None,
                'week_52_high': None,
                'week_52_low': None,
                'name': symbol.upper(),
                'exchange': 'UNKNOWN',
                'industry': 'Unknown',
                'source': 'unavailable'
            }
        }
        
        logger.info(f"Successfully returned data for {symbol} from {price_data['source']}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching market data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{symbol}/intraday")
async def get_intraday_data(
    symbol: str,
    days: int = Query(7, description="Number of days of intraday data", ge=1, le=30)
):
    """
    Fetch intraday (1-minute) candlestick data for last N days.
    Only available from Finnhub and AlphaVantage.
    
    - **symbol**: Ticker symbol (e.g., AAPL)
    - **days**: Number of days (default 7, max 30)
    """
    try:
        fetcher = get_market_data_fetcher()
        
        intraday_data = await fetcher.get_intraday_data(symbol.upper(), days)
        
        if not intraday_data:
            raise HTTPException(
                status_code=404,
                detail=f"Intraday data not available for {symbol}"
            )
        
        logger.info(f"Successfully returned intraday data for {symbol}")
        return intraday_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching intraday data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickers/search")
async def search_tickers_autocomplete(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Autocomplete search for tickers.
    Used for search dropdowns with 300ms debounce on frontend.
    
    - **q**: Search query (symbol or name)
    - **limit**: Max results (default 10)
    """
    async with get_session() as session:
        try:
            search_pattern = f"%{q.upper()}%"
            query = select(Ticker).where(
                (Ticker.symbol.ilike(search_pattern)) |
                (Ticker.name.ilike(search_pattern))
            ).order_by(Ticker.symbol).limit(limit)
            
            result = await session.execute(query)
            tickers = result.scalars().all()
            
            return [
                {
                    "symbol": t.symbol,
                    "name": t.name or t.symbol,
                    "exchange": t.exchange
                }
                for t in tickers
            ]
        except Exception as e:
            logger.error(f"Error searching tickers: {e}")
            return []


# WATCHLIST ENDPOINTS

@router.get("/watchlists")
async def list_watchlists():
    """List all watchlists with ticker counts."""
    async with get_session() as session:
        try:
            watchlists = await watchlist_service.get_all_watchlists(session)
            return [
                {
                    "id": str(w.id),
                    "name": w.name,
                    "description": w.description,
                    "ticker_count": len(w.tickers),
                    "tickers": [t.symbol for t in w.tickers],
                    "created_at": w.created_at.isoformat(),
                    "updated_at": w.updated_at.isoformat()
                }
                for w in watchlists
            ]
        except Exception as e:
            logger.error(f"Error listing watchlists: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlists", status_code=201)
async def create_new_watchlist(watchlist: WatchlistCreate):
    """Create a new watchlist."""
    async with get_session() as session:
        try:
            w = await watchlist_service.create_watchlist(
                session,
                name=watchlist.name,
                description=watchlist.description
            )
            return {
                "id": str(w.id),
                "name": w.name,
                "description": w.description,
                "created_at": w.created_at.isoformat()
            }
        except Exception as e:
            logger.error(f"Error creating watchlist: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlists/{watchlist_id}")
async def get_watchlist_detail(watchlist_id: str):
    """Get watchlist with all tickers and their latest prices."""
    async with get_session() as session:
        try:
            w = await watchlist_service.get_watchlist(session, watchlist_id)
            if not w:
                raise HTTPException(status_code=404, detail="Watchlist not found")
            
            return {
                "id": str(w.id),
                "name": w.name,
                "description": w.description,
                "ticker_count": len(w.tickers),
                "tickers": [
                    {
                        "symbol": t.symbol,
                        "name": t.name,
                        "exchange": t.exchange
                    }
                    for t in w.tickers
                ],
                "created_at": w.created_at.isoformat(),
                "updated_at": w.updated_at.isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching watchlist: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlists/{watchlist_id}/tickers")
async def add_ticker_to_watchlist_endpoint(
    watchlist_id: str,
    symbol: str = Query(..., description="Ticker symbol to add")
):
    """Add a ticker to a watchlist."""
    async with get_session() as session:
        try:
            success = await watchlist_service.add_ticker_to_watchlist(
                session,
                watchlist_id,
                symbol
            )
            if not success:
                raise HTTPException(status_code=404, detail="Watchlist not found")
            return {"message": f"Added {symbol} to watchlist", "success": True}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding ticker to watchlist: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/watchlists/{watchlist_id}/tickers/{symbol}")
async def remove_ticker_from_watchlist_endpoint(watchlist_id: str, symbol: str):
    """Remove a ticker from a watchlist."""
    async with get_session() as session:
        try:
            success = await watchlist_service.remove_ticker_from_watchlist(
                session,
                watchlist_id,
                symbol
            )
            return {"message": f"Removed {symbol} from watchlist", "success": success}
        except Exception as e:
            logger.error(f"Error removing ticker from watchlist: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/watchlists/{watchlist_id}")
async def delete_watchlist_endpoint(watchlist_id: str):
    """Delete a watchlist."""
    async with get_session() as session:
        try:
            success = await watchlist_service.delete_watchlist(session, watchlist_id)
            if not success:
                raise HTTPException(status_code=404, detail="Watchlist not found")
            return {"message": "Watchlist deleted", "success": True}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting watchlist: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# PORTFOLIO ENDPOINTS

@router.get("/portfolios")
async def list_portfolios():
    """List all portfolios with holdings summary."""
    async with get_session() as session:
        try:
            portfolios = await portfolio_service.get_all_portfolios(session)
            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description,
                    "inception_date": p.inception_date.isoformat(),
                    "initial_value": float(p.initial_value),
                    "holdings_count": len(p.holdings),
                    "holdings": [
                        {
                            "symbol": h.ticker.symbol,
                            "shares": float(h.shares),
                            "average_cost": float(h.average_cost) if h.average_cost else None
                        }
                        for h in p.holdings
                    ],
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat()
                }
                for p in portfolios
            ]
        except Exception as e:
            logger.error(f"Error listing portfolios: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolios", status_code=201)
async def create_new_portfolio(portfolio: PortfolioCreate):
    """Create a new portfolio."""
    async with get_session() as session:
        try:
            p = await portfolio_service.create_portfolio(
                session,
                name=portfolio.name,
                inception_date=portfolio.inception_date,
                initial_value=portfolio.initial_value,
                description=portfolio.description
            )
            return {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "inception_date": p.inception_date.isoformat(),
                "initial_value": float(p.initial_value),
                "created_at": p.created_at.isoformat()
            }
        except Exception as e:
            logger.error(f"Error creating portfolio: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolios/{portfolio_id}")
async def get_portfolio_detail(portfolio_id: str):
    """Get portfolio with all holdings and current values."""
    async with get_session() as session:
        try:
            p = await portfolio_service.get_portfolio(session, portfolio_id)
            if not p:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            
            return {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "inception_date": p.inception_date.isoformat(),
                "initial_value": float(p.initial_value),
                "holdings_count": len(p.holdings),
                "holdings": [
                    {
                        "symbol": h.ticker.symbol,
                        "name": h.ticker.name,
                        "shares": float(h.shares),
                        "average_cost": float(h.average_cost) if h.average_cost else None,
                        "added_at": h.added_at.isoformat()
                    }
                    for h in p.holdings
                ],
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching portfolio: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolios/{portfolio_id}/holdings")
async def add_portfolio_holding_endpoint(portfolio_id: str, holding: HoldingAdd):
    """Add or update a holding in a portfolio."""
    async with get_session() as session:
        try:
            h = await portfolio_service.add_holding(
                session,
                portfolio_id,
                holding.symbol,
                holding.shares,
                holding.average_cost
            )
            if not h:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            
            return {
                "message": f"Added {holding.shares} shares of {holding.symbol}",
                "holding": {
                    "symbol": holding.symbol,
                    "shares": holding.shares,
                    "average_cost": holding.average_cost
                },
                "success": True
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding holding: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/portfolios/{portfolio_id}/holdings/{symbol}")
async def remove_portfolio_holding_endpoint(portfolio_id: str, symbol: str):
    """Remove a holding from a portfolio."""
    async with get_session() as session:
        try:
            success = await portfolio_service.remove_holding(session, portfolio_id, symbol)
            return {"message": f"Removed {symbol} from portfolio", "success": success}
        except Exception as e:
            logger.error(f"Error removing holding: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/portfolios/{portfolio_id}")
async def delete_portfolio_endpoint(portfolio_id: str):
    """Delete a portfolio."""
    async with get_session() as session:
        try:
            success = await portfolio_service.delete_portfolio(session, portfolio_id)
            if not success:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            return {"message": "Portfolio deleted", "success": True}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting portfolio: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

