from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_session
from ..models import PriceDaily

RANGE_DAYS = {"1mo":31, "3mo":93, "6mo":186, "1y":372}  # MAX = 1y

async def _read_db(session: AsyncSession, symbol: str, start_ms: int) -> List[Dict]:
    stmt = (select(PriceDaily)
            .where(PriceDaily.symbol==symbol, PriceDaily.t_ms>=start_ms)
            .order_by(PriceDaily.t_ms))
    rows = (await session.execute(stmt)).scalars().all()
    return [ {"t":r.t_ms,"o":r.o,"h":r.h,"l":r.l,"c":r.c,"v":r.v} for r in rows ]

async def get_prices_1y(symbol: str, period: str) -> Dict:
    symbol = symbol.upper()
    if period not in RANGE_DAYS: period = "1y"
    now = datetime.now(timezone.utc)
    start_ms = int((now - timedelta(days=RANGE_DAYS[period])).timestamp()*1000)
    async with get_session() as session:
        candles = await _read_db(session, symbol, start_ms)
        return {"symbol": symbol, "candles": candles, "stale": False}

