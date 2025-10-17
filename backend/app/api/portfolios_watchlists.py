from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_session

router = APIRouter(prefix="/api", tags=["portfolio_watchlist"])

# ---------- WATCHLISTS ----------
class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

@router.get("/watchlists")
async def list_watchlists(session: AsyncSession = Depends(get_session)):
    # Get watchlists with their tickers
    res = await session.execute(text("""
        SELECT 
            w.id::text, 
            w.name, 
            w.created_at,
            COALESCE(
                json_agg(
                    json_build_object('symbol', t.symbol, 'added_at', wt.added_at)
                ) FILTER (WHERE t.symbol IS NOT NULL),
                '[]'::json
            ) as tickers
        FROM watchlist w
        LEFT JOIN watchlist_tickers wt ON w.id = wt.watchlist_id
        LEFT JOIN ticker t ON wt.ticker_id = t.id
        GROUP BY w.id, w.name, w.created_at
        ORDER BY w.created_at DESC
    """))
    return [dict(r._mapping) for r in res.fetchall()]

@router.post("/watchlists")
async def create_watchlist(payload: WatchlistCreate, session: AsyncSession = Depends(get_session)):
    q = text("INSERT INTO watchlist (name) VALUES (:name) RETURNING id::text, name, created_at")
    row = (await session.execute(q, {"name": payload.name})).first()
    await session.commit()
    return dict(row._mapping)

@router.delete("/watchlists/{watchlist_id}")
async def delete_watchlist(watchlist_id: str, session: AsyncSession = Depends(get_session)):
    res = await session.execute(text("DELETE FROM watchlist WHERE id = :id"), {"id": watchlist_id})
    await session.commit()
    return {"ok": True}

@router.get("/watchlists/{watchlist_id}/tickers")
async def list_watchlist_tickers(watchlist_id: str, session: AsyncSession = Depends(get_session)):
    res = await session.execute(text("""
        SELECT t.symbol, wt.added_at 
        FROM watchlist_tickers wt
        JOIN ticker t ON wt.ticker_id = t.id
        WHERE wt.watchlist_id = :id 
        ORDER BY wt.added_at DESC
    """), {"id": watchlist_id})
    return [dict(r._mapping) for r in res.fetchall()]

class WLAddTicker(BaseModel):
    symbol: str = Field(..., min_length=1)

@router.post("/watchlists/{watchlist_id}/tickers")
async def add_ticker(watchlist_id: str, payload: WLAddTicker, session: AsyncSession = Depends(get_session)):
    # First get the ticker_id from the symbol
    ticker_res = await session.execute(text("SELECT id FROM ticker WHERE symbol = :sym"), {"sym": payload.symbol.upper()})
    ticker_row = ticker_res.first()
    
    if not ticker_row:
        raise HTTPException(status_code=404, detail=f"Ticker {payload.symbol.upper()} not found")
    
    ticker_id = ticker_row.id
    
    # Now insert into watchlist_tickers
    q = text("""
        INSERT INTO watchlist_tickers (watchlist_id, ticker_id)
        VALUES (:watchlist_id, :ticker_id)
        ON CONFLICT (watchlist_id, ticker_id) DO NOTHING
        RETURNING added_at
    """)
    row = (await session.execute(q, {"watchlist_id": watchlist_id, "ticker_id": ticker_id})).first()
    await session.commit()
    
    if row:
        return {"symbol": payload.symbol.upper(), "added_at": row.added_at}
    else:
        return {"symbol": payload.symbol.upper(), "added_at": None, "exists": True}

@router.delete("/watchlists/{watchlist_id}/tickers/{symbol}")
async def remove_ticker(watchlist_id: str, symbol: str, session: AsyncSession = Depends(get_session)):
    await session.execute(text("""
        DELETE FROM watchlist_tickers 
        WHERE watchlist_id = :watchlist_id 
        AND ticker_id = (SELECT id FROM ticker WHERE symbol = :symbol)
    """), {"watchlist_id": watchlist_id, "symbol": symbol.upper()})
    await session.commit()
    return {"ok": True}

# ---------- PORTFOLIOS ----------
class PortfolioCreate(BaseModel):
    name: str
    inception_date: date
    initial_value: float = 0.0

@router.get("/portfolios")
async def list_portfolios(session: AsyncSession = Depends(get_session)):
    # Get portfolios with their holdings
    res = await session.execute(text("""
        SELECT 
            p.id::text, 
            p.name, 
            p.inception_date,
            p.initial_value,
            p.created_at,
            COALESCE(
                json_agg(
                    json_build_object('symbol', t.symbol, 'qty', ph.shares, 'avg_cost', ph.average_cost, 'as_of', ph.added_at)
                ) FILTER (WHERE t.symbol IS NOT NULL),
                '[]'::json
            ) as holdings
        FROM portfolio p
        LEFT JOIN portfolio_holding ph ON p.id = ph.portfolio_id
        LEFT JOIN ticker t ON ph.ticker_id = t.id
        GROUP BY p.id, p.name, p.inception_date, p.initial_value, p.created_at
        ORDER BY p.created_at DESC
    """))
    return [dict(r._mapping) for r in res.fetchall()]

@router.post("/portfolios")
async def create_portfolio(payload: PortfolioCreate, session: AsyncSession = Depends(get_session)):
    q = text("""
        INSERT INTO portfolio (name, inception_date, initial_value)
        VALUES (:name, :inc, :iv)
        RETURNING id::text, name, inception_date, initial_value, created_at
    """)
    row = (await session.execute(q, {"name": payload.name, "inc": payload.inception_date, "iv": payload.initial_value})).first()
    await session.commit()
    return dict(row._mapping)

@router.delete("/portfolios/{portfolio_id}")
async def delete_portfolio(portfolio_id: str, session: AsyncSession = Depends(get_session)):
    await session.execute(text("DELETE FROM portfolio WHERE id = :id"), {"id": portfolio_id})
    await session.commit()
    return {"ok": True}

# holdings
class HoldingUpsert(BaseModel):
    symbol: str
    qty: float
    avg_cost: float = 0.0  # Will be overridden by database price if as_of is provided
    as_of: Optional[date] = None  # If provided, will use open price from this date

@router.get("/portfolios/{portfolio_id}/holdings")
async def get_holdings(portfolio_id: str, session: AsyncSession = Depends(get_session)):
    res = await session.execute(text("""
        SELECT id::text, symbol, qty, avg_cost, as_of
        FROM portfolio_holding WHERE portfolio_id = :pid ORDER BY symbol
    """), {"pid": portfolio_id})
    return [dict(r._mapping) for r in res.fetchall()]

@router.post("/portfolios/{portfolio_id}/holdings")
async def upsert_holding(portfolio_id: str, h: HoldingUpsert, session: AsyncSession = Depends(get_session)):
    # First get the ticker_id from the symbol
    ticker_res = await session.execute(text("SELECT id FROM ticker WHERE symbol = :sym"), {"sym": h.symbol.upper()})
    ticker_row = ticker_res.first()
    
    if not ticker_row:
        raise HTTPException(status_code=404, detail=f"Ticker {h.symbol.upper()} not found in database")
    
    ticker_id = ticker_row.id
    
    # Get the open price for the selected date (or latest available date)
    price_res = await session.execute(text("""
        SELECT pd.open, pd.date
        FROM price_daily pd
        WHERE pd.ticker_id = :ticker_id
        AND pd.date <= COALESCE(:as_of, CURRENT_DATE)
        ORDER BY pd.date DESC
        LIMIT 1
    """), {"ticker_id": ticker_id, "as_of": h.as_of})
    
    price_row = price_res.first()
    if not price_row:
        raise HTTPException(status_code=404, detail=f"No price data found for {h.symbol.upper()} on {h.as_of or 'any date'}")
    
    # Use the open price from the database, or the provided avg_cost if no date specified
    actual_cost = float(price_row.open) if h.as_of else h.avg_cost
    
    q = text("""
        INSERT INTO portfolio_holding (portfolio_id, ticker_id, shares, average_cost, added_at)
        VALUES (:pid, :ticker_id, :shares, :avg_cost, COALESCE(:as_of, CURRENT_DATE))
        ON CONFLICT (portfolio_id, ticker_id)
        DO UPDATE SET shares = EXCLUDED.shares, average_cost = EXCLUDED.average_cost, added_at = EXCLUDED.added_at
        RETURNING id::text, shares, average_cost, added_at
    """)
    
    row = (await session.execute(q, {
        "pid": portfolio_id, 
        "ticker_id": ticker_id, 
        "shares": h.qty, 
        "avg_cost": actual_cost, 
        "as_of": h.as_of
    })).first()
    
    await session.commit()
    
    # Get the symbol for the response
    symbol_res = await session.execute(text("SELECT symbol FROM ticker WHERE id = :ticker_id"), {"ticker_id": ticker_id})
    symbol = symbol_res.first().symbol
    
    return {
        "id": row.id,
        "symbol": symbol,
        "qty": float(row.shares),
        "avg_cost": float(row.average_cost),
        "as_of": row.added_at
    }

@router.delete("/portfolios/{portfolio_id}/holdings/{symbol}")
async def delete_holding(portfolio_id: str, symbol: str, session: AsyncSession = Depends(get_session)):
    await session.execute(text("""
        DELETE FROM portfolio_holding 
        WHERE portfolio_id = :pid 
        AND ticker_id = (SELECT id FROM ticker WHERE symbol = :sym)
    """), {"pid": portfolio_id, "sym": symbol.upper()})
    await session.commit()
    return {"ok": True}


