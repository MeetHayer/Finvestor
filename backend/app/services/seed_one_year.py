from __future__ import annotations
import asyncio, csv, time, urllib.request, io
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from ..db import get_session
from ..models import PriceDaily

SYMS = ["SPY","QQQ","DIA","AAPL","MSFT","TSLA"]  # adjust to your CP#1 list

def _to_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return int(dt.timestamp()*1000)

async def _write_db(session: AsyncSession, symbol: str, rows: List[Dict]):
    if not rows: return
    chunk = 800
    for i in range(0, len(rows), chunk):
        part = rows[i:i+chunk]
        try:
            await session.execute(insert(PriceDaily).prefix_with("ON CONFLICT DO NOTHING"), part)
        except Exception:
            for v in part:
                try: await session.execute(insert(PriceDaily).values(**v))
                except Exception: pass
    await session.commit()

async def _fetch_yf(symbol: str) -> List[Dict]:
    # 1Y daily via yfinance
    df = yf.download(symbol, period="1y", interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        # second attempt
        df = yf.Ticker(symbol).history(period="1y", interval="1d", auto_adjust=False, actions=False)
    if df is None or df.empty:
        return []
    out = []
    for idx, r in df.dropna().iterrows():
        ts = idx.tz_localize(timezone.utc) if idx.tzinfo is None else idx.tz_convert(timezone.utc)
        out.append({
            "symbol": symbol,
            "t_ms": int(ts.timestamp()*1000),
            "o": float(r.get("Open",0.0)),
            "h": float(r.get("High",0.0)),
            "l": float(r.get("Low",0.0)),
            "c": float(r.get("Close",0.0)),
            "v": float(r.get("Volume",0.0)),
        })
    return out

def _stooq_csv(symbol: str) -> List[Dict]:
    # Stooq fallback: symbol.us
    url = f"https://stooq.com/q/d/l/?s={symbol.lower()}.us&i=d"
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    text = data.decode("utf-8", errors="ignore")
    rows = []
    today = datetime.now(timezone.utc)
    one_year_ago = today - timedelta(days=372)
    rdr = csv.DictReader(io.StringIO(text))
    for rec in rdr:
        if not rec.get("Date"): continue
        y,m,d = map(int, rec["Date"].split("-"))
        dt = datetime(y,m,d,tzinfo=timezone.utc)
        if dt < one_year_ago: continue  # keep last ~1y only
        rows.append({
            "symbol": symbol,
            "t_ms": int(dt.timestamp()*1000),
            "o": float(rec.get("Open") or 0),
            "h": float(rec.get("High") or 0),
            "l": float(rec.get("Low") or 0),
            "c": float(rec.get("Close") or 0),
            "v": float(rec.get("Volume") or 0),
        })
    return rows

async def seed_one_year():
    async with get_session() as session:
        for s in SYMS:
            # if we already have 200+ rows in the last year, skip
            cutoff = int((datetime.now(timezone.utc)-timedelta(days=372)).timestamp()*1000)
            have = (await session.execute(
                select(PriceDaily).where(PriceDaily.symbol==s, PriceDaily.t_ms>=cutoff)
            )).scalars().first()
            if have: 
                continue
            # try yfinance
            try:
                rows = await asyncio.to_thread(_fetch_yf, s)
                if not rows:
                    rows = await asyncio.to_thread(_stooq_csv, s)
            except Exception:
                rows = await asyncio.to_thread(_stooq_csv, s)
            await _write_db(session, s, rows)
            time.sleep(1.2)  # polite pause

