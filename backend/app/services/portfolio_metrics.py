"""
Portfolio metrics calculation service
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging

from app.models import Portfolio, PortfolioHolding, Ticker, PriceDaily, FundamentalsCache

logger = logging.getLogger(__name__)


async def calculate_portfolio_metrics(session: AsyncSession, portfolio_id: str) -> Dict:
    """
    Calculate simple portfolio metrics:
    - Current portfolio value
    - Portfolio return (% change since inception)
    """
    from sqlalchemy import text
    from collections import defaultdict
    
    # Check if portfolio exists
    p_check = await session.execute(text("SELECT inception_date, COALESCE(initial_value,0) as initial_value FROM portfolio WHERE id = :pid"), {"pid": portfolio_id})
    p_row = p_check.first()
    
    if not p_row:
        return None
    
    inception_date = p_row.inception_date
    initial_value = float(p_row.initial_value or 0)
    
    # Calculate current portfolio value
    try:
        # Get all transactions to build current position state
        all_tx_res = await session.execute(text("""
            SELECT symbol, side, qty, price
            FROM portfolio_transaction
            WHERE portfolio_id = :pid
            ORDER BY trade_date ASC, created_at ASC
        """), {"pid": portfolio_id})
        all_txs = [dict(r._mapping) for r in all_tx_res.fetchall()]
        
        if not all_txs:
            # No transactions yet, value = initial cash
            current_value = initial_value
        else:
            # Build current positions
            positions = defaultdict(float)
            running_cash = initial_value
            
            for t in all_txs:
                q = float(t['qty'] or 0)
                px = float(t['price'] or 0)
                if t['side'] == 'BUY':
                    positions[t['symbol']] += q
                    running_cash -= q * px
                elif t['side'] == 'SELL':
                    positions[t['symbol']] -= q
                    running_cash += q * px
            
            # Get current prices for holdings
            symbols = [s for s, q in positions.items() if q > 0]
            holdings_value = 0.0
            
            if symbols:
                px_res = await session.execute(text("""
                    SELECT t.symbol, pd.close
                    FROM ticker t
                    JOIN price_daily pd ON pd.ticker_id = t.id
                    WHERE t.symbol = ANY(:symbols) 
                      AND pd.date = (
                          SELECT MAX(pd2.date) 
                          FROM price_daily pd2 
                          WHERE pd2.ticker_id = t.id
                      )
                """), {"symbols": symbols})
                prices = {r.symbol: float(r.close or 0) for r in px_res.fetchall()}
                
                for symbol, qty in positions.items():
                    if qty > 0 and symbol in prices:
                        holdings_value += qty * prices[symbol]
            
            current_value = running_cash + holdings_value
        
        # Calculate portfolio return
        portfolio_return = ((current_value - initial_value) / initial_value * 100) if initial_value > 0 else 0.0
        
        return {
            "portfolio_return": float(portfolio_return),  # % return since inception
            "current_value": float(current_value),
            "initial_value": float(initial_value),
            "gain_loss": float(current_value - initial_value)
        }
    
    except Exception as e:
        logger.exception(f"Failed to calculate portfolio metrics: {e}")
        return {
            "portfolio_return": 0.0,
            "current_value": initial_value,
            "initial_value": initial_value,
            "gain_loss": 0.0
        }

async def calculate_watchlist_metrics(session: AsyncSession, watchlist_id: str) -> Dict:
    """
    Calculate watchlist metrics including:
    - Current price for each ticker
    - Daily change ($, %)
    - Weekly change ($, %)
    - Market cap
    - P/E ratio
    - Beta
    """
    from app.models import Watchlist
    
    # Get watchlist with tickers
    stmt = select(Watchlist).where(Watchlist.id == watchlist_id).options(
        selectinload(Watchlist.tickers)
    )
    result = await session.execute(stmt)
    watchlist = result.scalar_one_or_none()
    
    if not watchlist:
        return None
    
    ticker_metrics = []
    
    for ticker in watchlist.tickers:
        # Get latest price
        latest_stmt = select(PriceDaily).where(
            PriceDaily.ticker_id == ticker.id
        ).order_by(PriceDaily.date.desc()).limit(1)
        latest_result = await session.execute(latest_stmt)
        latest = latest_result.scalar_one_or_none()
        
        if not latest:
            continue
        
        current_price = float(latest.close)
        
        # Get price from 1 day ago
        one_day_ago = latest.date - timedelta(days=1)
        day_ago_stmt = select(PriceDaily).where(
            PriceDaily.ticker_id == ticker.id,
            PriceDaily.date <= one_day_ago
        ).order_by(PriceDaily.date.desc()).limit(1)
        day_ago_result = await session.execute(day_ago_stmt)
        day_ago = day_ago_result.scalar_one_or_none()
        
        daily_change_dollar = 0.0
        daily_change_pct = 0.0
        if day_ago:
            prev_price = float(day_ago.close)
            daily_change_dollar = current_price - prev_price
            daily_change_pct = (daily_change_dollar / prev_price * 100) if prev_price > 0 else 0
        
        # Get price from 7 days ago
        week_ago = latest.date - timedelta(days=7)
        week_ago_stmt = select(PriceDaily).where(
            PriceDaily.ticker_id == ticker.id,
            PriceDaily.date <= week_ago
        ).order_by(PriceDaily.date.desc()).limit(1)
        week_ago_result = await session.execute(week_ago_stmt)
        week_ago = week_ago_result.scalar_one_or_none()
        
        weekly_change_dollar = 0.0
        weekly_change_pct = 0.0
        if week_ago:
            prev_week_price = float(week_ago.close)
            weekly_change_dollar = current_price - prev_week_price
            weekly_change_pct = (weekly_change_dollar / prev_week_price * 100) if prev_week_price > 0 else 0
        
        # Get fundamentals
        fund_stmt = select(FundamentalsCache).where(
            FundamentalsCache.ticker_id == ticker.id
        )
        fund_result = await session.execute(fund_stmt)
        fundamentals = fund_result.scalar_one_or_none()
        
        ticker_metrics.append({
            'symbol': ticker.symbol,
            'name': ticker.name,
            'current_price': current_price,
            'daily_change_dollar': daily_change_dollar,
            'daily_change_pct': daily_change_pct,
            'weekly_change_dollar': weekly_change_dollar,
            'weekly_change_pct': weekly_change_pct,
            'market_cap': int(fundamentals.market_cap) if fundamentals and fundamentals.market_cap else None,
            'pe_ratio': float(fundamentals.pe_ratio) if fundamentals and fundamentals.pe_ratio else None,
            'beta': float(fundamentals.beta) if fundamentals and fundamentals.beta else None,
            'week_52_high': float(fundamentals.week_52_high) if fundamentals and fundamentals.week_52_high else None,
            'week_52_low': float(fundamentals.week_52_low) if fundamentals and fundamentals.week_52_low else None,
        })
    
    return {
        'watchlist_id': str(watchlist.id),
        'name': watchlist.name,
        'description': watchlist.description,
        'num_tickers': len(ticker_metrics),
        'tickers': ticker_metrics
    }

