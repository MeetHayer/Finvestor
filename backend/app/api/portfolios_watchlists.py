from fastapi import APIRouter, HTTPException, Depends
import logging
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.portfolio_metrics import calculate_portfolio_metrics
from datetime import datetime, date, timedelta

from app.db import get_session, SessionLocal

# Define router early so decorators can reference it
router = APIRouter(prefix="/api", tags=["portfolio_watchlist"])
log = logging.getLogger(__name__)
async def _close_for_date_db(session: AsyncSession, symbol: str, d):
    """
    Get close price from DB for a specific date.
    Only accepts prices within 1 day of the target date to avoid using stale data.
    """
    from datetime import timedelta
    
    sym = symbol.upper()
    max_lookback = timedelta(days=1)
    
    # Try exact date
    row = (await session.execute(text("""
        SELECT pd.close, pd.date FROM price_daily pd JOIN ticker t ON t.id=pd.ticker_id
        WHERE t.symbol=:sym AND pd.date=:d LIMIT 1
    """), {"sym": sym, "d": d})).first()
    if row: 
        return float(row[0])
    
    # Try prior date (within 30 days)
    row = (await session.execute(text("""
        SELECT pd.close, pd.date FROM price_daily pd JOIN ticker t ON t.id=pd.ticker_id
        WHERE t.symbol=:sym AND pd.date<:d AND pd.date >= :min_date
        ORDER BY pd.date DESC LIMIT 1
    """), {"sym": sym, "d": d, "min_date": d - max_lookback})).first()
    if row:
        log.info(f"Using DB price for {sym} from {row[1]} (target: {d})")
        return float(row[0])
    
    # Try next date (within 1 day)
    row = (await session.execute(text("""
        SELECT pd.close, pd.date FROM price_daily pd JOIN ticker t ON t.id=pd.ticker_id
        WHERE t.symbol=:sym AND pd.date>:d AND pd.date <= :max_date
        ORDER BY pd.date ASC LIMIT 1
    """), {"sym": sym, "d": d, "max_date": d + max_lookback})).first()
    if row:
        log.info(f"Using DB price for {sym} from {row[1]} (target: {d})")
        return float(row[0])
    
    # No recent price in DB
    raise HTTPException(status_code=404, detail=f"No recent price (within 1 day) in DB for {sym} on {d}")


# --- Helpers to adapt to schema differences without breaking other features ---
async def table_has_column(session: AsyncSession, table_name: str, column_name: str) -> bool:
    q = text(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = :t AND column_name = :c
        LIMIT 1
        """
    )
    res = await session.execute(q, {"t": table_name, "c": column_name})
    return res.first() is not None

async def first_existing_column(session: AsyncSession, table: str, candidates: list[str]) -> str:
    for col in candidates:
        if await table_has_column(session, table, col):
            return col
    # Fallback to first; SQL will error but we want visibility
    return candidates[0]

# Emergency minimal endpoint to bypass schema differences and confirm data path
@router.get("/portfolios/min")
async def list_portfolios_min(session: AsyncSession = Depends(get_session)):
    res = await session.execute(text(
        """
        SELECT 
            p.id::text,
            p.name,
            p.inception_date,
            p.initial_value
        FROM portfolio p
        ORDER BY p.name ASC
        """
    ))
    rows = [dict(r._mapping) for r in res.fetchall()]
    for r in rows:
        r["cash"] = None
        r["created_at"] = None
        r["holdings"] = []
    return rows


# ---------- WATCHLISTS ----------
class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

@router.get("/watchlists")
async def list_watchlists(session: AsyncSession = Depends(get_session)):
    # Detect whether association table uses ticker_id or symbol
    has_ticker_id = await table_has_column(session, "watchlist_tickers", "ticker_id")
    if has_ticker_id:
        join_sql = "LEFT JOIN ticker t ON wt.ticker_id = t.id"
        symbol_expr = "t.symbol"
    else:
        join_sql = "LEFT JOIN ticker t ON wt.symbol = t.symbol"
        symbol_expr = "COALESCE(t.symbol, wt.symbol)"

    sql = f"""
        SELECT 
            w.id::text, 
            w.name, 
            w.created_at,
            COALESCE(
                json_agg(
                    json_build_object('symbol', {symbol_expr}, 'added_at', wt.added_at)
                ) FILTER (WHERE {symbol_expr} IS NOT NULL),
                '[]'::json
            ) as tickers
        FROM watchlist w
        LEFT JOIN watchlist_tickers wt ON w.id = wt.watchlist_id
        {join_sql}
        GROUP BY w.id, w.name, w.created_at
        ORDER BY w.created_at DESC
    """
    res = await session.execute(text(sql))
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
    has_ticker_id = await table_has_column(session, "watchlist_tickers", "ticker_id")
    sym = payload.symbol.upper()

    if has_ticker_id:
        # Resolve ticker_id from symbol
        ticker_res = await session.execute(text("SELECT id FROM ticker WHERE symbol = :sym"), {"sym": sym})
        ticker_row = ticker_res.first()
        if not ticker_row:
            raise HTTPException(status_code=404, detail=f"Ticker {sym} not found")
        q = text(
            """
            INSERT INTO watchlist_tickers (watchlist_id, ticker_id)
            VALUES (:watchlist_id, :ticker_id)
            ON CONFLICT (watchlist_id, ticker_id) DO NOTHING
            RETURNING added_at
            """
        )
        row = (await session.execute(q, {"watchlist_id": watchlist_id, "ticker_id": ticker_row.id})).first()
    else:
        # Use symbol directly
        q = text(
            """
            INSERT INTO watchlist_tickers (watchlist_id, symbol)
            VALUES (:watchlist_id, :symbol)
            ON CONFLICT (watchlist_id, symbol) DO NOTHING
            RETURNING added_at
            """
        )
        row = (await session.execute(q, {"watchlist_id": watchlist_id, "symbol": sym})).first()

    await session.commit()
    return {"symbol": sym, "added_at": row.added_at if row else None, "exists": row is None}

@router.delete("/watchlists/{watchlist_id}/tickers/{symbol}")
async def remove_ticker(watchlist_id: str, symbol: str, session: AsyncSession = Depends(get_session)):
    has_ticker_id = await table_has_column(session, "watchlist_tickers", "ticker_id")
    if has_ticker_id:
        sql = """
            DELETE FROM watchlist_tickers 
            WHERE watchlist_id = :watchlist_id 
            AND ticker_id = (SELECT id FROM ticker WHERE symbol = :symbol)
        """
        params = {"watchlist_id": watchlist_id, "symbol": symbol.upper()}
    else:
        sql = """
            DELETE FROM watchlist_tickers 
            WHERE watchlist_id = :watchlist_id 
            AND symbol = :symbol
        """
        params = {"watchlist_id": watchlist_id, "symbol": symbol.upper()}
    await session.execute(text(sql), params)
    await session.commit()
    return {"ok": True}

# ---------- PORTFOLIOS ----------
class PortfolioCreate(BaseModel):
    name: str
    inception_date: date
    initial_value: float = 0.0

@router.get("/portfolios")
async def list_portfolios(session: AsyncSession = Depends(get_session)):
    # Clear any aborted transaction state from prior errors
    try:
        await session.rollback()
    except Exception:
        pass
    try:
        # Detect varying column names in portfolio_holding
        qty_col = await first_existing_column(session, "portfolio_holding", ["shares", "qty", "quantity"])  # numeric
        avg_col = await first_existing_column(session, "portfolio_holding", ["average_cost", "avg_cost", "average_price"])  # numeric
        has_tid = await table_has_column(session, "portfolio_holding", "ticker_id")
        # Build join and symbol expression depending on schema
        if has_tid:
            join_clause = "LEFT JOIN ticker t ON ph.ticker_id = t.id"
            sym_expr = "t.symbol"
        else:
            join_clause = "LEFT JOIN ticker t ON t.symbol = ph.symbol"
            sym_expr = "COALESCE(t.symbol, ph.symbol)"
        # Some schemas may not have 'cash' column; if missing, derive from initial_value - holdings cost using detected column names
        has_cash = await table_has_column(session, "portfolio", "cash")
        if has_cash:
            cash_select = "p.cash"
        else:
            # initial_value - sum(buys) + sum(sells) using ledger when cash column is missing
            cash_select = (
                f"(COALESCE(p.initial_value, 0) "
                f" + COALESCE((SELECT SUM(l.amount) FROM portfolio_cash_ledger l WHERE l.portfolio_id = p.id), 0) "
                f" )"
            )
        asof_col = await first_existing_column(session, "portfolio_holding", ["added_at", "as_of", "created_at"])  # timestamp/date

        col_qty = f"ph.{qty_col}"
        col_avg = f"ph.{avg_col}"
        col_asof = f"ph.{asof_col}"

        sql = f"""
            SELECT 
                p.id::text, 
                p.name, 
                p.inception_date,
                p.initial_value,
                {cash_select} as cash,
                p.created_at,
                COALESCE((
                    SELECT json_agg(json_build_object(
                        'symbol', {sym_expr},
                        'qty', {col_qty},
                        'avg_cost', {col_avg},
                        'as_of', {col_asof}
                    ))
                    FROM portfolio_holding ph
                    {join_clause}
                    WHERE ph.portfolio_id = p.id
                ), '[]'::json) AS holdings
            FROM portfolio p
            ORDER BY p.created_at DESC
        """
        res = await session.execute(text(sql))
        return [dict(r._mapping) for r in res.fetchall()]
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass
        # Minimal fallback to guarantee 200 even on heterogeneous schemas
        minimal_sql = """
            SELECT 
                p.id::text,
                p.name,
                p.inception_date,
                p.initial_value
            FROM portfolio p
            ORDER BY p.name ASC
        """
        # Use a fresh session in case the injected one is stuck in an aborted state
        async with SessionLocal() as fresh:
            try:
                await fresh.rollback()
            except Exception:
                pass
            res = await fresh.execute(text(minimal_sql))
            rows = [dict(r._mapping) for r in res.fetchall()]
            for r in rows:
                try:
                    has_cash_fb = await table_has_column(fresh, "portfolio", "cash")
                    if has_cash_fb:
                        cash_row = await fresh.execute(text("SELECT cash FROM portfolio WHERE id = :id"), {"id": r["id"]})
                        cr = cash_row.first()
                        r["cash"] = float(cr.cash) if cr and cr.cash is not None else 0.0
                    else:
                        # Detect column names for fallback derivation
                        fb_qty = await first_existing_column(fresh, "portfolio_holding", ["shares", "qty", "quantity"])  # numeric
                        fb_avg = await first_existing_column(fresh, "portfolio_holding", ["average_cost", "avg_cost", "average_price"])  # numeric
                        cash_sql = f"""
                            SELECT 
                                COALESCE(p.initial_value, 0) - 
                                COALESCE((SELECT SUM(ph.{fb_qty} * COALESCE(ph.{fb_avg}, 0)) FROM portfolio_holding ph WHERE ph.portfolio_id = p.id), 0) AS cash
                            FROM portfolio p WHERE p.id = :id
                        """
                        cash_row = await fresh.execute(text(cash_sql), {"id": r["id"]})
                        cr = cash_row.first()
                        r["cash"] = float(cr.cash) if cr else 0.0
                except Exception:
                    r["cash"] = None
                r["created_at"] = None
                r["holdings"] = []
            return rows

@router.post("/portfolios")
async def create_portfolio(payload: PortfolioCreate, session: AsyncSession = Depends(get_session)):
    # Clear any aborted state
    try:
        await session.rollback()
    except Exception:
        pass

    has_cash = await table_has_column(session, "portfolio", "cash")
    params = {
        "name": payload.name,
        "inc": payload.inception_date,
        "iv": payload.initial_value,
        "cash": payload.initial_value if payload.initial_value is not None else 0,
    }

    if has_cash:
        q = text(
            """
            INSERT INTO portfolio (name, inception_date, initial_value, cash)
            VALUES (:name, :inc, :iv, :cash)
            RETURNING id::text, name, inception_date, initial_value, cash, created_at
            """
        )
    else:
        q = text(
            """
            INSERT INTO portfolio (name, inception_date, initial_value)
            VALUES (:name, :inc, :iv)
            RETURNING id::text, name, inception_date, initial_value, initial_value as cash, created_at
            """
        )

    try:
        row = (await session.execute(q, params)).first()
        await session.commit()
        return dict(row._mapping)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create portfolio: {e}")

@router.delete("/portfolios/{portfolio_id}")
async def delete_portfolio(portfolio_id: str, session: AsyncSession = Depends(get_session)):
    await session.execute(text("DELETE FROM portfolio WHERE id = :id"), {"id": portfolio_id})
    await session.commit()
    return {"ok": True}

# holdings
class HoldingUpsert(BaseModel):
    symbol: str
    qty: float
    avg_cost: Optional[float] = None  # Optional - will auto-fill from DB if None
    as_of: Optional[date] = None  # Trade date - used for auto-pricing if avg_cost is None

@router.get("/portfolios/{portfolio_id}/holdings")
async def get_holdings(portfolio_id: str, session: AsyncSession = Depends(get_session)):
    # Detect column/schema differences dynamically
    qty_col = await first_existing_column(session, "portfolio_holding", ["shares", "qty", "quantity"])  # numeric
    avg_col = await first_existing_column(session, "portfolio_holding", ["average_cost", "avg_cost", "average_price"])  # numeric
    asof_col = await first_existing_column(session, "portfolio_holding", ["added_at", "as_of", "created_at"])  # timestamp/date
    has_tid = await table_has_column(session, "portfolio_holding", "ticker_id")
    if has_tid:
        sql = f"""
            SELECT ph.id::text AS id, t.symbol AS symbol, ph.{qty_col} AS qty, ph.{avg_col} AS avg_cost, ph.{asof_col} AS as_of
            FROM portfolio_holding ph
            JOIN ticker t ON t.id = ph.ticker_id
            WHERE ph.portfolio_id = :pid
            ORDER BY t.symbol
        """
    else:
        sql = f"""
            SELECT ph.id::text AS id, ph.symbol AS symbol, ph.{qty_col} AS qty, ph.{avg_col} AS avg_cost, ph.{asof_col} AS as_of
            FROM portfolio_holding ph
            WHERE ph.portfolio_id = :pid
            ORDER BY ph.symbol
        """
    res = await session.execute(text(sql), {"pid": portfolio_id})
    return [dict(r._mapping) for r in res.fetchall()]

async def get_avg_price_or_prior(session: AsyncSession, ticker_id: str, target_date: date) -> Optional[float]:
    """
    Resolve a trade price for a date using layered fallbacks:
      1) From DB: prefer close on the date; else open; else (high+low)/2; search nearest prior ≤10 days
      2) Finnhub candle close for target date (if API key present)
      3) Alpha Vantage daily close for target date (if API key present)
    """
    from datetime import timedelta, datetime
    import os, requests

    # 1) DB lookup for target date or nearest prior within 3 days (weekend/holiday)
    for i in range(4):  # 0..3
        check_date = target_date - timedelta(days=i)
        res = await session.execute(text("""
            SELECT open, high, low, close FROM price_daily 
            WHERE ticker_id = :ticker_id AND date = :date
        """), {"ticker_id": ticker_id, "date": check_date})
        row = res.first()
        if row:
            if row.close is not None:
                return float(row.close)
            if row.open is not None:
                return float(row.open)
            if row.high is not None and row.low is not None:
                return (float(row.high) + float(row.low)) / 2

    # Resolve symbol for API fallbacks
    sym_row = await session.execute(text("SELECT symbol FROM ticker WHERE id = :id"), {"id": ticker_id})
    sr = sym_row.first()
    symbol = sr.symbol if sr else None
    if not symbol:
        return None

    # 2) Finnhub daily candle close
    finnhub_key = os.getenv('FINNHUB_KEY') or os.getenv('FINNHUB_API_KEY')
    if finnhub_key:
        try:
            # UNIX range for target_date (00:00 to 23:59)
            start = int(datetime(target_date.year, target_date.month, target_date.day, 0, 0).timestamp())
            end = int(datetime(target_date.year, target_date.month, target_date.day, 23, 59).timestamp())
            r = requests.get(
                'https://finnhub.io/api/v1/stock/candle',
                params={'symbol': symbol.upper(), 'resolution': 'D', 'from': start, 'to': end, 'token': finnhub_key},
                timeout=8
            )
            j = r.json()
            if j and j.get('s') == 'ok' and j.get('c'):
                return float(j['c'][0])
        except Exception:
            pass

    # 3) Alpha Vantage daily close (exact date)
    av_key = os.getenv('ALPHA_VANTAGE_KEY') or os.getenv('ALPHAVANTAGE_KEY')
    if av_key:
        try:
            r = requests.get(
                'https://www.alphavantage.co/query',
                params={'function': 'TIME_SERIES_DAILY', 'symbol': symbol.upper(), 'apikey': av_key, 'outputsize': 'compact'},
                timeout=10
            )
            j = r.json()
            ts = j.get('Time Series (Daily)') or {}
            ds = target_date.strftime('%Y-%m-%d')
            if ds in ts and '4. close' in ts[ds]:
                return float(ts[ds]['4. close'])
        except Exception:
            pass

    # 4) yfinance exact-date close as a final fallback
    try:
        import yfinance as yf
        start_dt = datetime(target_date.year, target_date.month, target_date.day)
        end_dt = start_dt + timedelta(days=1)
        hist = yf.Ticker(symbol.upper()).history(start=start_dt, end=end_dt, interval='1d', auto_adjust=False)
        if hist is not None and not hist.empty:
            close_val = hist['Close'].iloc[-1]
            if close_val is not None:
                return float(close_val)
    except Exception:
        pass

    # No broad fallbacks: if we cannot resolve the exact trade date (or the immediately prior business day),
    # we return None so the caller can ask for manual avg_cost. This preserves correct cost basis integrity.

    return None


@router.post("/portfolios/{portfolio_id}/holdings")
async def upsert_holding(portfolio_id: str, h: HoldingUpsert, session: AsyncSession = Depends(get_session)):
    try:
        # Basic payload validation for clearer 422s
        if not getattr(h, 'symbol', None) or not isinstance(h.symbol, str) or not h.symbol.strip():
            raise HTTPException(status_code=422, detail="symbol is required")
        if getattr(h, 'qty', None) is None:
            raise HTTPException(status_code=422, detail="qty is required")
        try:
            if float(h.qty) <= 0:
                raise HTTPException(status_code=422, detail="qty must be a positive number")
        except Exception:
            raise HTTPException(status_code=422, detail="qty must be a number")
        # Resolve ticker_id (for pricing) and detect schema link (ticker_id vs symbol)
        ticker_res = await session.execute(text("SELECT id FROM ticker WHERE symbol = :sym"), {"sym": h.symbol.upper()})
        ticker_row = ticker_res.first()
        if not ticker_row:
            raise HTTPException(status_code=404, detail=f"Ticker {h.symbol.upper()} not found in database")
        ticker_id = ticker_row.id
        has_tid = await table_has_column(session, "portfolio_holding", "ticker_id")

        # Determine trade date (use as_of if provided, else today)
        from datetime import date as datetime_date
        trade_date = h.as_of if h.as_of else datetime_date.today()

        # Enforce trade date must be on/after portfolio inception date
        inc_res = await session.execute(text("""
            SELECT inception_date FROM portfolio WHERE id = :pid
        """), {"pid": portfolio_id})
        inc_row = inc_res.first()
        if not inc_row or not inc_row.inception_date:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        if trade_date < inc_row.inception_date:
            raise HTTPException(
                status_code=400,
                detail=f"Trade date {trade_date} is before portfolio inception {inc_row.inception_date}"
            )

        # Determine avg_cost (treat 0 or null as missing -> auto compute)
        provide_cost = (getattr(h, 'avg_cost', None) is not None)
        try:
            provide_cost = provide_cost and float(h.avg_cost) > 0
        except Exception:
            provide_cost = False

        if provide_cost:
            actual_cost = float(h.avg_cost)
        else:
            # ALWAYS try DB first - it has our seeded historical data which is correct
            actual_cost = None
            try:
                actual_cost = await _close_for_date_db(session, h.symbol.upper(), trade_date)
                log.info(f"✅ Got price from DB for {h.symbol.upper()} on {trade_date}: ${actual_cost:.2f}")
            except Exception as e:
                log.info(f"⚠️  No DB price for {h.symbol.upper()} on {trade_date}, trying external APIs: {e}")
                # Only use external APIs if DB has no data
                # Try yahooquery as fallback
                try:
                    import yahooquery as yq
                    ticker = yq.Ticker(h.symbol.upper())
                    # Get historical data around the trade date
                    hist = ticker.history(start=str(trade_date - timedelta(days=5)), end=str(trade_date + timedelta(days=1)))
                    if hist is not None and not hist.empty:
                        hist = hist.reset_index()
                        # Find exact date or closest
                        for _, r in hist.iterrows():
                            row_date = r.get('date')
                            if hasattr(row_date, 'date'):
                                row_date = row_date.date()
                            if row_date == trade_date:
                                actual_cost = float(r.get('close', 0) or 0)
                                log.info(f"✅ Got price from yahooquery for {h.symbol.upper()} on {trade_date}: ${actual_cost:.2f}")
                                break
                        if actual_cost is None and len(hist) > 0:
                            # Use last available price
                            actual_cost = float(hist.iloc[-1].get('close', 0) or 0)
                            log.info(f"✅ Got closest price from yahooquery for {h.symbol.upper()}: ${actual_cost:.2f}")
                except Exception as api_err:
                    log.warning(f"yahooquery failed for {h.symbol.upper()}: {api_err}")
                    actual_cost = None
            
            if actual_cost is None or actual_cost <= 0:
                raise HTTPException(
                    status_code=422,
                    detail=f"No price available to auto-fill average_cost for {h.symbol.upper()} on {trade_date}. "
                           f"Please provide avg_cost manually or choose a different date."
                )

        # Calculate total cost and validate cash balance
        total_cost = actual_cost * h.qty

        # Get current cash balance (support schemas without cash column)
        has_cash = await table_has_column(session, "portfolio", "cash")
        if has_cash:
            cash_res = await session.execute(text("""
                SELECT cash FROM portfolio WHERE id = :pid
            """), {"pid": portfolio_id})
            cash_row = cash_res.first()
            current_cash = float(cash_row.cash) if cash_row and cash_row.cash is not None else 0.0
        else:
            # Derive cash = initial_value - sum(holdings cost) with dynamic column names
            d_qty = await first_existing_column(session, "portfolio_holding", ["shares", "qty", "quantity"])  # numeric
            d_avg = await first_existing_column(session, "portfolio_holding", ["average_cost", "avg_cost", "average_price"])  # numeric
            derive_sql = f"""
                SELECT 
                    COALESCE(p.initial_value, 0) - 
                    COALESCE((SELECT SUM(ph.{d_qty} * COALESCE(ph.{d_avg}, 0)) FROM portfolio_holding ph WHERE ph.portfolio_id = p.id), 0) AS cash
                FROM portfolio p
                WHERE p.id = :pid
            """
            cash_res = await session.execute(text(derive_sql), {"pid": portfolio_id})
            cash_row = cash_res.first()
            current_cash = float(cash_row.cash) if cash_row else 0.0

        if total_cost > current_cash:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient cash. Need ${total_cost:.2f}, but only have ${current_cash:.2f} available."
            )

        # Note: Cash will be updated after transaction recording via transaction replay

        # Detect actual holding column names
        qty_col = await first_existing_column(session, "portfolio_holding", ["shares", "qty", "quantity"])  # numeric
        avg_col = await first_existing_column(session, "portfolio_holding", ["average_cost", "avg_cost", "average_price"])  # numeric
        asof_col = await first_existing_column(session, "portfolio_holding", ["added_at", "as_of", "created_at"])  # timestamp/date

        # Upsert without relying on ON CONFLICT (some schemas may lack the constraint)
        if has_tid:
            exists_row = (await session.execute(text(
                "SELECT id FROM portfolio_holding WHERE portfolio_id = :pid AND ticker_id = :tid"
            ), {"pid": portfolio_id, "tid": ticker_id})).first()
        else:
            exists_row = (await session.execute(text(
                "SELECT id FROM portfolio_holding WHERE portfolio_id = :pid AND symbol = :sym"
            ), {"pid": portfolio_id, "sym": h.symbol.upper()})).first()
        if exists_row:
            if has_tid:
                upd_sql = f"""
                    UPDATE portfolio_holding 
                    SET {qty_col} = :shares, {avg_col} = :avg_cost, {asof_col} = :trade_date
                    WHERE portfolio_id = :pid AND ticker_id = :ticker_id
                    RETURNING id::text AS id, {qty_col} AS shares, {avg_col} AS average_cost, {asof_col} AS added_at
                """
                row = (await session.execute(text(upd_sql), {
                    "pid": portfolio_id,
                    "ticker_id": ticker_id,
                    "shares": h.qty,
                    "avg_cost": actual_cost,
                    "trade_date": trade_date
                })).first()
            else:
                upd_sql = f"""
                    UPDATE portfolio_holding 
                    SET {qty_col} = :shares, {avg_col} = :avg_cost, {asof_col} = :trade_date
                    WHERE portfolio_id = :pid AND symbol = :sym
                    RETURNING id::text AS id, {qty_col} AS shares, {avg_col} AS average_cost, {asof_col} AS added_at
                """
                row = (await session.execute(text(upd_sql), {
                    "pid": portfolio_id,
                    "sym": h.symbol.upper(),
                    "shares": h.qty,
                    "avg_cost": actual_cost,
                    "trade_date": trade_date
                })).first()
        else:
            if has_tid:
                ins_sql = f"""
                    INSERT INTO portfolio_holding (portfolio_id, ticker_id, {qty_col}, {avg_col}, {asof_col})
                    VALUES (:pid, :ticker_id, :shares, :avg_cost, :trade_date)
                    RETURNING id::text AS id, {qty_col} AS shares, {avg_col} AS average_cost, {asof_col} AS added_at
                """
                row = (await session.execute(text(ins_sql), {
                    "pid": portfolio_id,
                    "ticker_id": ticker_id,
                    "shares": h.qty,
                    "avg_cost": actual_cost,
                    "trade_date": trade_date
                })).first()
            else:
                ins_sql = f"""
                    INSERT INTO portfolio_holding (portfolio_id, symbol, {qty_col}, {avg_col}, {asof_col})
                    VALUES (:pid, :sym, :shares, :avg_cost, :trade_date)
                    RETURNING id::text AS id, {qty_col} AS shares, {avg_col} AS average_cost, {asof_col} AS added_at
                """
                row = (await session.execute(text(ins_sql), {
                    "pid": portfolio_id,
                    "sym": h.symbol.upper(),
                    "shares": h.qty,
                    "avg_cost": actual_cost,
                    "trade_date": trade_date
                })).first()

        # Extract data from row BEFORE committing (row becomes stale after commit)
        holding_id = row.id
        holding_shares = float(row.shares)
        holding_avg_cost = float(row.average_cost)
        holding_added_at = row.added_at
        
        await session.commit()

        # Get the symbol for the response
        symbol_res = await session.execute(text("SELECT symbol FROM ticker WHERE id = :ticker_id"), {"ticker_id": ticker_id})
        _row = symbol_res.first()
        symbol = _row.symbol if _row else h.symbol.upper()

        # Record transaction (BUY) with proper remaining_cash chronology
        try:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS portfolio_transaction (
                    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                    portfolio_id UUID NOT NULL,
                    symbol TEXT NOT NULL,
                    ticker_id UUID,
                    side TEXT NOT NULL,                -- 'BUY'|'SELL'
                    qty NUMERIC(18,6) NOT NULL,
                    price NUMERIC(18,6) NOT NULL,
                    amount NUMERIC(18,2) NOT NULL,     -- signed cash flow (+/-)
                    remaining_cash NUMERIC(18,2),      -- cash after this transaction
                    trade_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            # Ensure remaining_cash column exists
            await session.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='portfolio_transaction' AND column_name='remaining_cash'
                    ) THEN
                        ALTER TABLE portfolio_transaction ADD COLUMN remaining_cash NUMERIC(18,2);
                    END IF;
                END $$;
            """))
            
            # Insert the new transaction first (without remaining_cash)
            delta = -float(total_cost)
            await session.execute(text("""
                INSERT INTO portfolio_transaction (portfolio_id, symbol, ticker_id, side, qty, price, amount, trade_date)
                VALUES (:pid, :sym, :tid, 'BUY', :qty, :price, :amt, :td)
            """), {
                "pid": portfolio_id,
                "sym": symbol,
                "tid": str(ticker_id),
                "qty": float(h.qty),
                "price": float(actual_cost),
                "amt": delta,
                "td": trade_date
            })
            
            # Recompute ALL remaining_cash values from scratch in chronological order
            # Fetch initial value
            ivr = await session.execute(text("SELECT COALESCE(initial_value,0) FROM portfolio WHERE id = :pid"), {"pid": portfolio_id})
            iv_row = ivr.first()
            initial = float(iv_row[0]) if iv_row else 0.0
            
            # Fetch all transactions
            all_tx_result = await session.execute(text("""
                SELECT id, amount FROM portfolio_transaction
                WHERE portfolio_id = :pid
                ORDER BY trade_date ASC, created_at ASC
            """), {"pid": portfolio_id})
            all_txs = [(str(r[0]), float(r[1] or 0.0)) for r in all_tx_result.fetchall()]
            
            running = initial
            final_cash = initial
            for tx_id, tx_amount in all_txs:
                running += tx_amount
                if running < -1e-6:
                    await session.rollback()
                    raise HTTPException(status_code=400, detail=f"Transaction on {trade_date} would cause negative cash balance (${running:.2f}). Transaction blocked.")
                await session.execute(text("""
                    UPDATE portfolio_transaction SET remaining_cash = :rc WHERE id = :id
                """), {"rc": running, "id": tx_id})
                final_cash = running  # Track the final cash value
            
            # Update portfolio.cash to match the latest transaction's remaining_cash
            await session.execute(text("""
                UPDATE portfolio SET cash = :cash WHERE id = :pid
            """), {"cash": final_cash, "pid": portfolio_id})
            
            await session.commit()
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            log.exception(f"Transaction recording failed for {symbol}: {e}")
            # Transaction recording failed - rollback the holding too
            raise HTTPException(status_code=500, detail=f"Transaction recording failed: {str(e)}")

        # Get final cash after all commits
        if has_cash:
            final_cash_res = await session.execute(text("SELECT cash FROM portfolio WHERE id = :pid"), {"pid": portfolio_id})
            final_cash_row = final_cash_res.first()
            final_cash = float(final_cash_row.cash) if final_cash_row and final_cash_row.cash is not None else 0.0
        else:
            final_cash = current_cash - total_cost

        return {
            "id": holding_id,
            "symbol": symbol,
            "qty": holding_shares,
            "avg_cost": holding_avg_cost,
            "as_of": holding_added_at,
            "auto_priced": h.avg_cost is None,
            "total_cost": total_cost,
            "remaining_cash": final_cash
        }
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add holding: {str(e)}")

class SellHolding(BaseModel):
    qty: float  # Number of shares to sell

@router.post("/portfolios/{portfolio_id}/holdings/{symbol}/sell")
async def sell_holding(portfolio_id: str, symbol: str, payload: SellHolding, session: AsyncSession = Depends(get_session)):
    """
    Sell shares from a holding and add proceeds to portfolio cash.
    Uses last business day close price.
    """
    import requests
    import os
    
    try:
        # Get ticker_id and current holding
        has_tid = await table_has_column(session, "portfolio_holding", "ticker_id")
        qty_col = await first_existing_column(session, "portfolio_holding", ["shares", "qty", "quantity"])  # numeric
        if has_tid:
            res = await session.execute(text(f"""
                SELECT ph.{qty_col} AS shares, t.id as ticker_id, t.symbol
                FROM portfolio_holding ph
                JOIN ticker t ON ph.ticker_id = t.id
                WHERE ph.portfolio_id = :pid AND t.symbol = :sym
            """), {"pid": portfolio_id, "sym": symbol.upper()})
        else:
            res = await session.execute(text(f"""
                SELECT ph.{qty_col} AS shares, t.id as ticker_id, t.symbol
                FROM portfolio_holding ph
                JOIN ticker t ON t.symbol = ph.symbol
                WHERE ph.portfolio_id = :pid AND t.symbol = :sym
            """), {"pid": portfolio_id, "sym": symbol.upper()})
        
        holding = res.first()
        if not holding:
            raise HTTPException(status_code=404, detail=f"Holding {symbol} not found in portfolio")
        
        # Allow selling up to all shares with float tolerance
        qty_req = float(payload.qty)
        owned = float(holding.shares)
        eps = 1e-9
        if qty_req > owned + eps:
            raise HTTPException(status_code=400, detail=f"Cannot sell {payload.qty} shares, only {holding.shares} available")
        
        # Get latest price: try DB first, then yahooquery
        current_price = None
        price_res = await session.execute(text("""
            SELECT close FROM price_daily 
            WHERE ticker_id = :ticker_id 
            ORDER BY date DESC LIMIT 1
        """), {"ticker_id": str(holding.ticker_id)})
        price_row = price_res.first()
        if price_row and price_row.close is not None:
            current_price = float(price_row.close)

        # If DB has nothing, use yahooquery for latest price
        if not current_price:
            try:
                import yahooquery as yq
                ticker = yq.Ticker(symbol.upper())
                quote = ticker.price
                if quote and symbol.upper() in quote:
                    price_data = quote[symbol.upper()]
                    current_price = float(price_data.get('regularMarketPrice', 0) or 0)
            except Exception as e:
                log.warning(f"yahooquery failed for latest price {symbol}: {e}")
        
        # Final fallback: Finnhub then Alpha Vantage
        if not current_price:
            api_key = os.getenv('FINNHUB_KEY') or os.getenv('FINNHUB_API_KEY')
            if api_key:
                try:
                    response = requests.get(
                        f"https://finnhub.io/api/v1/quote",
                        params={'symbol': symbol.upper(), 'token': api_key},
                        timeout=10
                    )
                    quote = response.json()
                    if quote and 'c' in quote:
                        current_price = float(quote['c'])
                except Exception as e:
                    log.warning(f"Failed to fetch current price for {symbol}: {e}")
        if not current_price:
            av_key = os.getenv('ALPHA_VANTAGE_KEY') or os.getenv('ALPHAVANTAGE_KEY')
            if av_key:
                try:
                    r = requests.get(
                        'https://www.alphavantage.co/query',
                        params={'function': 'TIME_SERIES_DAILY', 'symbol': symbol.upper(), 'apikey': av_key, 'outputsize': 'compact'},
                        timeout=10
                    )
                    j = r.json()
                    ts = j.get('Time Series (Daily)') or {}
                    # last business day close
                    if ts:
                        last_key = sorted(ts.keys())[-1]
                        c = ts[last_key].get('4. close')
                        if c is not None:
                            current_price = float(c)
                except Exception:
                    pass
        
        if not current_price:
            raise HTTPException(status_code=500, detail=f"Could not fetch current price for {symbol}")
        
        # Calculate proceeds
        proceeds = float(payload.qty) * current_price
        
        # Update holding or delete if selling all
        if qty_req >= owned - eps:
            # Sell all - delete holding
            if has_tid:
                await session.execute(text("""
                    DELETE FROM portfolio_holding 
                    WHERE portfolio_id = :pid AND ticker_id = :tid
                """), {"pid": portfolio_id, "tid": str(holding.ticker_id)})
            else:
                await session.execute(text("""
                    DELETE FROM portfolio_holding 
                    WHERE portfolio_id = :pid AND symbol = :sym
                """), {"pid": portfolio_id, "sym": symbol.upper()})
        else:
            # Partial sell - reduce shares
            if has_tid:
                await session.execute(text(f"""
                    UPDATE portfolio_holding 
                    SET {qty_col} = {qty_col} - :qty 
                    WHERE portfolio_id = :pid AND ticker_id = :tid
                """), {"pid": portfolio_id, "tid": str(holding.ticker_id), "qty": float(payload.qty)})
            else:
                await session.execute(text(f"""
                    UPDATE portfolio_holding 
                    SET {qty_col} = {qty_col} - :qty 
                WHERE portfolio_id = :pid AND symbol = :sym
            """), {"pid": portfolio_id, "sym": symbol.upper(), "qty": float(payload.qty)})
        
        # Note: Cash will be updated after transaction recording via transaction replay
        
        # Record transaction (SELL) with proper remaining_cash chronology
        try:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS portfolio_transaction (
                    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                    portfolio_id UUID NOT NULL,
                    symbol TEXT NOT NULL,
                    ticker_id UUID,
                    side TEXT NOT NULL,
                    qty NUMERIC(18,6) NOT NULL,
                    price NUMERIC(18,6) NOT NULL,
                    amount NUMERIC(18,2) NOT NULL,
                    remaining_cash NUMERIC(18,2),
                    trade_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            # Ensure remaining_cash column exists
            await session.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='portfolio_transaction' AND column_name='remaining_cash'
                    ) THEN
                        ALTER TABLE portfolio_transaction ADD COLUMN remaining_cash NUMERIC(18,2);
                    END IF;
                END $$;
            """))
            
            # Insert the new transaction first (without remaining_cash)
            delta = float(proceeds)
            await session.execute(text("""
                INSERT INTO portfolio_transaction (portfolio_id, symbol, ticker_id, side, qty, price, amount, trade_date)
                VALUES (:pid, :sym, :tid, 'SELL', :qty, :price, :amt, CURRENT_DATE)
            """), {
                "pid": portfolio_id,
                "sym": symbol.upper(),
                "tid": str(holding.ticker_id),
                "qty": float(qty_req),
                "price": float(current_price),
                "amt": delta
            })
            
            # Recompute ALL remaining_cash values from scratch in chronological order
            # Fetch initial value
            ivr = await session.execute(text("SELECT COALESCE(initial_value,0) FROM portfolio WHERE id = :pid"), {"pid": portfolio_id})
            iv_row = ivr.first()
            initial = float(iv_row[0]) if iv_row else 0.0
            
            # Fetch all transactions
            all_tx_result = await session.execute(text("""
                SELECT id, amount FROM portfolio_transaction
                WHERE portfolio_id = :pid
                ORDER BY trade_date ASC, created_at ASC
            """), {"pid": portfolio_id})
            all_txs = [(str(r[0]), float(r[1] or 0.0)) for r in all_tx_result.fetchall()]
            
            running = initial
            final_cash = initial
            for tx_id, tx_amount in all_txs:
                running += tx_amount
                if running < -1e-6:
                    await session.rollback()
                    raise HTTPException(status_code=400, detail=f"Transaction would cause negative cash balance (${running:.2f}). Transaction blocked.")
                await session.execute(text("""
                    UPDATE portfolio_transaction SET remaining_cash = :rc WHERE id = :id
                """), {"rc": running, "id": tx_id})
                final_cash = running  # Track the final cash value
            
            # Update portfolio.cash to match the latest transaction's remaining_cash
            await session.execute(text("""
                UPDATE portfolio SET cash = :cash WHERE id = :pid
            """), {"cash": final_cash, "pid": portfolio_id})
            
            await session.commit()
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            log.error(f"Sell transaction recording failed: {e}")
        
        return {
            "ok": True,
            "sold_shares": float(payload.qty),
            "price_per_share": round(current_price, 2),
            "proceeds": round(proceeds, 2),
            "remaining_shares": max(0, float(holding.shares) - float(payload.qty)),
            "cash": final_cash  # Return the accurate final cash
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Sell holding error: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.delete("/portfolios/{portfolio_id}/holdings/{symbol}")
async def delete_holding(portfolio_id: str, symbol: str, session: AsyncSession = Depends(get_session)):
    await session.execute(text("""
        DELETE FROM portfolio_holding 
        WHERE portfolio_id = :pid 
        AND ticker_id = (SELECT id FROM ticker WHERE symbol = :sym)
    """), {"pid": portfolio_id, "sym": symbol.upper()})
    await session.commit()
    return {"ok": True}


@router.get("/portfolios/{portfolio_id}/transactions")
async def list_transactions(portfolio_id: str, session: AsyncSession = Depends(get_session)):
    """
    Return a simple transaction log for a portfolio.
    If the table does not exist yet, return an empty list.
    """
    try:
        chk = await session.execute(text("""
            SELECT 1 FROM information_schema.tables WHERE table_name = 'portfolio_transaction' LIMIT 1
        """))
        if chk.first() is None:
            return []

        res = await session.execute(text("""
            SELECT id::text, symbol, side, qty, price, amount, remaining_cash, trade_date, created_at
            FROM portfolio_transaction
            WHERE portfolio_id = :pid
            ORDER BY trade_date DESC, created_at DESC
        """), {"pid": portfolio_id})
        return [dict(r._mapping) for r in res.fetchall()]
    except Exception as e:
        log.exception("list_transactions error")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolios/{portfolio_id}/metrics")
async def portfolio_metrics(portfolio_id: str, session: AsyncSession = Depends(get_session)):
    try:
        return await calculate_portfolio_metrics(session, portfolio_id)
    except Exception as e:
        log.exception("metrics error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolios/{portfolio_id}/risk")
async def portfolio_risk_metrics(portfolio_id: str, session: AsyncSession = Depends(get_session)):
    """
    Get portfolio risk metrics:
    - Annualized volatility
    - Sharpe ratio (using risk-free rate)
    - Max drawdown
    - 1-day 95% VaR (historical method)
    """
    try:
        from app.services.portfolio_metrics import calculate_portfolio_risk_metrics
        from datetime import date
        
        metrics = await calculate_portfolio_risk_metrics(session, portfolio_id)
        
        if metrics is None:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        return {
            "portfolio_id": portfolio_id,
            "as_of": date.today().isoformat(),
            "metrics": metrics
        }
    except HTTPException:
        raise
    except Exception as e:
        log.exception("risk metrics error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolios/{portfolio_id}/value_series")
async def portfolio_value_series(portfolio_id: str, days: int = 365, session: AsyncSession = Depends(get_session)):
    """
    Builds a daily value series for the portfolio from inception to last business day.
    Prefers transaction-driven reconstruction (cash and positions) if the transaction
    table exists; otherwise falls back to current holdings snapshot.
    """
    try:
        # Portfolio inception
        p_row = await session.execute(text("SELECT inception_date, COALESCE(initial_value,0) FROM portfolio WHERE id = :id"), {"id": portfolio_id})
        p = p_row.first()
        if not p or not p.inception_date:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        inception = p.inception_date
        today = date.today()
        # Always start from inception to show full portfolio history
        start = inception

        # If we have a transaction table, reconstruct positions+cash over time
        has_tx = False
        try:
            chk = await session.execute(text("""
                SELECT 1 FROM information_schema.tables WHERE table_name = 'portfolio_transaction' LIMIT 1
            """))
            has_tx = chk.first() is not None
        except Exception:
            has_tx = False

        if has_tx:
            tx_res = await session.execute(text("""
                SELECT symbol, side, qty, price, amount, trade_date
                FROM portfolio_transaction
                WHERE portfolio_id = :pid AND trade_date >= :start
                ORDER BY trade_date ASC
            """), {"pid": portfolio_id, "start": start})
            txs = [dict(r._mapping) for r in tx_res.fetchall()]
            symbols = sorted(list({t['symbol'] for t in txs}))
            # Pull all closes for symbols since start
            px_res = await session.execute(text("""
                SELECT t.symbol, pd.date, pd.close
                FROM ticker t
                JOIN price_daily pd ON pd.ticker_id = t.id
                WHERE t.symbol = ANY(:symbols) AND pd.date >= :start
                ORDER BY pd.date ASC
            """), {"symbols": symbols, "start": start})
            rows = [dict(r._mapping) for r in px_res.fetchall()]
            # Build date->symbol->close and running last close map
            from collections import defaultdict
            closes_by_date = defaultdict(dict)
            for r in rows:
                closes_by_date[r['date']][r['symbol']] = float(r['close'] or 0)
            last_close = {s: None for s in symbols}
            # Running positions and cash
            positions = defaultdict(float)
            running_cash = float(p[1])  # initial_value
            # Index txs by date
            tx_by_date = defaultdict(list)
            for t in txs:
                tx_by_date[t['trade_date']].append(t)

            out = []
            d = start
            while d <= today:
                # apply transactions for day d
                for t in tx_by_date.get(d, []):
                    q = float(t['qty'] or 0)
                    px = float(t['price'] or 0)
                    if t['side'] == 'BUY':
                        positions[t['symbol']] += q
                        running_cash += -q * px
                    elif t['side'] == 'SELL':
                        positions[t['symbol']] -= q
                        running_cash += q * px
                # update last closes
                for s, c in closes_by_date.get(d, {}).items():
                    last_close[s] = c
                # compute value = cash + sum(pos*last_close)
                val = running_cash
                for s, q in positions.items():
                    lc = last_close.get(s)
                    if lc is not None:
                        val += q * lc
                ts = int(datetime.combine(d, datetime.min.time()).timestamp() * 1000)
                out.append([ts, float(val)])
                d += timedelta(days=1)
            return {"series": out}

        # Fallback: snapshot holdings-based series for last N days
        qty_col = await first_existing_column(session, "portfolio_holding", ["shares", "qty", "quantity"])  # numeric
        has_tid = await table_has_column(session, "portfolio_holding", "ticker_id")
        if has_tid:
            hsql = f"SELECT t.symbol AS symbol, ph.{qty_col} AS qty FROM portfolio_holding ph JOIN ticker t ON t.id = ph.ticker_id WHERE ph.portfolio_id = :pid"
        else:
            hsql = f"SELECT ph.symbol AS symbol, ph.{qty_col} AS qty FROM portfolio_holding ph WHERE ph.portfolio_id = :pid"
        res = await session.execute(text(hsql), {"pid": portfolio_id})
        holdings = [dict(r._mapping) for r in res.fetchall()]
        symbols = [h['symbol'] for h in holdings]
        qty_by_symbol = {h['symbol']: float(h['qty'] or 0) for h in holdings}
        # Cash via column or ledger
        cash = 0.0
        if await table_has_column(session, "portfolio", "cash"):
            cr = await session.execute(text("SELECT cash FROM portfolio WHERE id = :id"), {"id": portfolio_id})
            row = cr.first()
            if row and row[0] is not None:
                cash = float(row[0])
        else:
            lr = await session.execute(text("SELECT COALESCE(SUM(amount),0) FROM portfolio_cash_ledger WHERE portfolio_id = :pid"), {"pid": portfolio_id})
            amt = lr.first()
            cash = float(p[1]) + float(amt[0] if amt and amt[0] is not None else 0)

        if not symbols:
            out = []
            d = start
            while d <= today:
                ts = int(datetime.combine(d, datetime.min.time()).timestamp() * 1000)
                out.append([ts, cash])
                d += timedelta(days=1)
            return {"series": out}

        px_res = await session.execute(text("""
            SELECT t.symbol, pd.date, pd.close
            FROM ticker t
            JOIN price_daily pd ON pd.ticker_id = t.id
            WHERE t.symbol = ANY(:symbols) AND pd.date >= :start
            ORDER BY pd.date
        """), {"symbols": symbols, "start": start})
        rows = [dict(r._mapping) for r in px_res.fetchall()]
        from collections import defaultdict
        closes_by_date = defaultdict(dict)
        for r in rows:
            closes_by_date[r['date']][r['symbol']] = float(r['close'] or 0)
        last_close = {s: None for s in symbols}
        out = []
        d = start
        while d <= today:
            for s, c in closes_by_date.get(d, {}).items():
                last_close[s] = c
            val = cash
            for s, q in qty_by_symbol.items():
                lc = last_close.get(s)
                if lc is not None:
                    val += q * lc
            ts = int(datetime.combine(d, datetime.min.time()).timestamp() * 1000)
            out.append([ts, float(val)])
            d += timedelta(days=1)
        return {"series": out}
    except Exception as e:
        log.exception("value_series error")
        raise HTTPException(status_code=500, detail=str(e))

