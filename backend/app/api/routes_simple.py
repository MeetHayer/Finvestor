from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import Optional, List
import logging

from app.db import get_session
from app.models import Ticker, PriceDaily, Watchlist, Portfolio, PortfolioHolding
from app.services.market_data import get_market_data_fetcher

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

# ---- Search tickers ----
@router.get("/search")
async def search_tickers(q: str = Query(..., min_length=1)):
    async with get_session() as session:
        q_like = f"%{q.upper()}%"
        stmt = select(Ticker).where(
            (func.upper(Ticker.symbol).like(q_like)) | (func.upper(Ticker.name).like(q_like))
        ).limit(25)
        results = (await session.execute(stmt)).scalars().all()
        if results:
            return [{"symbol": t.symbol, "name": t.name, "exchange": t.exchange} for t in results]
        # fallback: minimal yfinance search
        import yfinance as yf
        try:
            info = yf.Ticker(q.upper()).info
            name = info.get("shortName") or info.get("longName") or q.upper()
            return [{"symbol": q.upper(), "name": name, "exchange": info.get("exchange", "N/A")}]
        except Exception:
            return []

# ---- Market data ----
@router.get("/data/{symbol}")
async def get_market_data(symbol: str, range_days: int = 365):
    fetcher = get_market_data_fetcher()
    try:
        data = await fetcher.fetch(symbol.upper(), range_days=range_days)
        if not data:
            raise HTTPException(status_code=404, detail="No data available")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("market data error")
        raise HTTPException(status_code=500, detail=str(e))

# ---- Watchlists ----
from pydantic import BaseModel, Field

class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

@router.get("/watchlists")
async def list_watchlists():
    async with get_session() as session:
        items = (await session.execute(select(Watchlist))).scalars().all()
        return [{"id": str(w.id), "name": w.name} for w in items]

@router.post("/watchlists")
async def create_watchlist(payload: WatchlistCreate):
    async with get_session() as session:
        w = Watchlist(name=payload.name)
        session.add(w)
        await session.commit()
        await session.refresh(w)
        return {"id": str(w.id), "name": w.name}

@router.delete("/watchlists/{watchlist_id}")
async def delete_watchlist(watchlist_id: str):
    async with get_session() as session:
        w = await session.get(Watchlist, watchlist_id)
        if not w: raise HTTPException(404, "not found")
        await session.delete(w)
        await session.commit()
        return {"ok": True}

# ---- Portfolios ----
class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    inception_date: date
    initial_value: float = Field(ge=0, default=0.0)

@router.get("/portfolios")
async def list_portfolios():
    async with get_session() as session:
        items = (await session.execute(select(Portfolio))).scalars().all()
        return [{"id": str(p.id), "name": p.name, "inception_date": str(p.inception_date), "initial_value": float(p.initial_value)} for p in items]

@router.post("/portfolios")
async def create_portfolio(payload: PortfolioCreate):
    async with get_session() as session:
        p = Portfolio(name=payload.name, inception_date=payload.inception_date, initial_value=payload.initial_value)
        session.add(p)
        await session.commit()
        await session.refresh(p)
        return {"id": str(p.id), "name": p.name, "inception_date": str(p.inception_date), "initial_value": float(p.initial_value)}

@router.delete("/portfolios/{portfolio_id}")
async def delete_portfolio(portfolio_id: str):
    async with get_session() as session:
        p = await session.get(Portfolio, portfolio_id)
        if not p: raise HTTPException(404, "not found")
        await session.delete(p)
        await session.commit()
        return {"ok": True}





