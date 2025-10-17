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
    Calculate comprehensive portfolio metrics including:
    - Total value
    - Total cost basis
    - Total return ($)
    - Total return (%)
    - Holding period return for each position
    - Average beta
    - Individual position metrics
    """
    
    # Get portfolio with holdings
    stmt = select(Portfolio).where(Portfolio.id == portfolio_id).options(
        selectinload(Portfolio.holdings).selectinload(PortfolioHolding.ticker)
    )
    result = await session.execute(stmt)
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        return None
    
    total_value = 0.0
    total_cost = 0.0
    weighted_beta_sum = 0.0
    position_metrics = []
    
    for holding in portfolio.holdings:
        # Get current price
        latest_price_stmt = select(PriceDaily).where(
            PriceDaily.ticker_id == holding.ticker_id
        ).order_by(PriceDaily.date.desc()).limit(1)
        latest_price_result = await session.execute(latest_price_stmt)
        latest_price = latest_price_result.scalar_one_or_none()
        
        if not latest_price:
            continue
        
        current_price = float(latest_price.close)
        cost_basis = float(holding.average_cost) if holding.average_cost else 0
        shares = float(holding.shares)
        
        # Calculate position metrics
        position_value = current_price * shares
        position_cost = cost_basis * shares
        position_return_dollar = position_value - position_cost
        position_return_pct = (position_return_dollar / position_cost * 100) if position_cost > 0 else 0
        
        # Calculate holding period (days)
        holding_period_days = (date.today() - holding.added_at.date()).days
        
        # Get beta from fundamentals
        beta_stmt = select(FundamentalsCache).where(
            FundamentalsCache.ticker_id == holding.ticker_id
        )
        beta_result = await session.execute(beta_stmt)
        fundamentals = beta_result.scalar_one_or_none()
        beta = float(fundamentals.beta) if fundamentals and fundamentals.beta else 1.0
        
        # Add to totals
        total_value += position_value
        total_cost += position_cost
        weighted_beta_sum += beta * position_value
        
        position_metrics.append({
            'symbol': holding.ticker.symbol,
            'name': holding.ticker.name,
            'shares': shares,
            'cost_basis': cost_basis,
            'current_price': current_price,
            'position_value': position_value,
            'position_cost': position_cost,
            'return_dollar': position_return_dollar,
            'return_pct': position_return_pct,
            'holding_period_days': holding_period_days,
            'beta': beta,
            'weight': 0  # Will calculate after we have total_value
        })
    
    # Calculate position weights
    for pos in position_metrics:
        pos['weight'] = (pos['position_value'] / total_value * 100) if total_value > 0 else 0
    
    # Calculate portfolio-level metrics
    total_return_dollar = total_value - total_cost
    total_return_pct = (total_return_dollar / total_cost * 100) if total_cost > 0 else 0
    average_beta = (weighted_beta_sum / total_value) if total_value > 0 else 1.0
    
    # Calculate portfolio return since inception
    inception_days = (date.today() - portfolio.inception_date).days
    initial_value = float(portfolio.initial_value) if portfolio.initial_value else total_cost
    portfolio_return_dollar = total_value - initial_value
    portfolio_return_pct = (portfolio_return_dollar / initial_value * 100) if initial_value > 0 else 0
    
    return {
        'portfolio_id': str(portfolio.id),
        'name': portfolio.name,
        'inception_date': str(portfolio.inception_date),
        'inception_days': inception_days,
        'initial_value': initial_value,
        'current_value': total_value,
        'total_cost': total_cost,
        'total_return_dollar': total_return_dollar,
        'total_return_pct': total_return_pct,
        'portfolio_return_dollar': portfolio_return_dollar,
        'portfolio_return_pct': portfolio_return_pct,
        'average_beta': average_beta,
        'num_positions': len(position_metrics),
        'positions': position_metrics
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




