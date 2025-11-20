"""
Portfolio metrics calculation service
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging
import numpy as np

from app.models import Portfolio, PortfolioHolding, Ticker, PriceDaily, FundamentalsCache, RiskFreeSeries

logger = logging.getLogger(__name__)


async def calculate_portfolio_metrics(session: AsyncSession, portfolio_id: str) -> Dict:
    """
    Calculate simple portfolio metrics:
    - Current portfolio value (using same logic as value_series for consistency)
    - Portfolio return (% change since inception)
    
    This function uses the EXACT same calculation as value_series endpoint
    to ensure metrics match the graph.
    """
    from sqlalchemy import text
    from collections import defaultdict
    from datetime import date, datetime, timedelta
    
    # Check if portfolio exists
    p_check = await session.execute(text("SELECT inception_date, COALESCE(initial_value,0) as initial_value FROM portfolio WHERE id = :pid"), {"pid": portfolio_id})
    p_row = p_check.first()
    
    if not p_row:
        return None
    
    inception_date = p_row.inception_date
    initial_value = float(p_row.initial_value or 0)
    today = date.today()
    
    # Use the SAME logic as value_series endpoint
    try:
        # Check if transaction table exists
        has_tx = False
        try:
            chk = await session.execute(text("""
                SELECT 1 FROM information_schema.tables WHERE table_name = 'portfolio_transaction' LIMIT 1
            """))
            has_tx = chk.first() is not None
        except Exception:
            has_tx = False
        
        if has_tx:
            # Get all transactions from inception
            tx_res = await session.execute(text("""
                SELECT symbol, side, qty, price, trade_date
                FROM portfolio_transaction
                WHERE portfolio_id = :pid AND trade_date >= :start
                ORDER BY trade_date ASC, created_at ASC
            """), {"pid": portfolio_id, "start": inception_date})
            txs = [dict(r._mapping) for r in tx_res.fetchall()]
            
            if not txs:
                current_value = initial_value
            else:
                symbols = sorted(list({t['symbol'] for t in txs}))
                
                # Get all price data for symbols from inception to today
                px_res = await session.execute(text("""
                    SELECT t.symbol, pd.date, pd.close
                    FROM ticker t
                    JOIN price_daily pd ON pd.ticker_id = t.id
                    WHERE t.symbol = ANY(:symbols) AND pd.date >= :start
                    ORDER BY pd.date ASC
                """), {"symbols": symbols, "start": inception_date})
                rows = [dict(r._mapping) for r in px_res.fetchall()]
                
                # Build date->symbol->close map
                closes_by_date = defaultdict(dict)
                for r in rows:
                    closes_by_date[r['date']][r['symbol']] = float(r['close'] or 0)
                
                last_close = {s: None for s in symbols}
                positions = defaultdict(float)
                running_cash = initial_value
                
                # Index transactions by date
                tx_by_date = defaultdict(list)
                for t in txs:
                    tx_by_date[t['trade_date']].append(t)
                
                # Process day by day to get the LATEST value (same as value_series)
                d = inception_date
                current_value = initial_value
                
                while d <= today:
                    # Apply transactions for this day
                    for t in tx_by_date.get(d, []):
                        q = float(t['qty'] or 0)
                        px = float(t['price'] or 0)
                        if t['side'] == 'BUY':
                            positions[t['symbol']] += q
                            running_cash -= q * px
                        elif t['side'] == 'SELL':
                            positions[t['symbol']] -= q
                            running_cash += q * px
                    
                    # Update last known prices for this day
                    for s, c in closes_by_date.get(d, {}).items():
                        last_close[s] = c
                    
                    # Calculate value for this day (same formula as value_series)
                    val = running_cash
                    for s, q in positions.items():
                        lc = last_close.get(s)
                        if lc is not None:
                            val += q * lc
                    
                    current_value = val  # Keep updating until we reach today
                    d += timedelta(days=1)
        else:
            # Fallback: use current holdings snapshot (same as value_series fallback)
            # Import helper functions from portfolios_watchlists
            async def table_has_column(session: AsyncSession, table_name: str, column_name: str) -> bool:
                q = text("SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c LIMIT 1")
                res = await session.execute(q, {"t": table_name, "c": column_name})
                return res.first() is not None
            
            async def first_existing_column(session: AsyncSession, table: str, candidates: list) -> str:
                for col in candidates:
                    if await table_has_column(session, table, col):
                        return col
                return candidates[0]
            
            qty_col = await first_existing_column(session, "portfolio_holding", ["shares", "qty", "quantity"])
            has_tid = await table_has_column(session, "portfolio_holding", "ticker_id")
            
            if has_tid:
                hsql = f"SELECT t.symbol AS symbol, ph.{qty_col} AS qty FROM portfolio_holding ph JOIN ticker t ON t.id = ph.ticker_id WHERE ph.portfolio_id = :pid"
            else:
                hsql = f"SELECT ph.symbol AS symbol, ph.{qty_col} AS qty FROM portfolio_holding ph WHERE ph.portfolio_id = :pid"
            
            res = await session.execute(text(hsql), {"pid": portfolio_id})
            holdings = [dict(r._mapping) for r in res.fetchall()]
            symbols = [h['symbol'] for h in holdings]
            qty_by_symbol = {h['symbol']: float(h['qty'] or 0) for h in holdings}
            
            # Get cash
            cash = 0.0
            if await table_has_column(session, "portfolio", "cash"):
                cr = await session.execute(text("SELECT cash FROM portfolio WHERE id = :id"), {"id": portfolio_id})
                row = cr.first()
                if row and row[0] is not None:
                    cash = float(row[0])
            else:
                lr = await session.execute(text("SELECT COALESCE(SUM(amount),0) FROM portfolio_cash_ledger WHERE portfolio_id = :pid"), {"pid": portfolio_id})
                amt = lr.first()
                cash = initial_value + float(amt[0] if amt and amt[0] is not None else 0)
            
            if not symbols:
                current_value = cash
            else:
                # Get latest prices (same as value_series fallback logic)
                px_res = await session.execute(text("""
                    SELECT t.symbol, pd.date, pd.close
                    FROM ticker t
                    JOIN price_daily pd ON pd.ticker_id = t.id
                    WHERE t.symbol = ANY(:symbols) AND pd.date >= :start
                    ORDER BY pd.date DESC
                """), {"symbols": symbols, "start": inception_date})
                rows = [dict(r._mapping) for r in px_res.fetchall()]
                
                # Get most recent price for each symbol
                last_close = {}
                seen_symbols = set()
                for r in rows:
                    if r['symbol'] not in seen_symbols:
                        last_close[r['symbol']] = float(r['close'] or 0)
                        seen_symbols.add(r['symbol'])
                
                val = cash
                for s, q in qty_by_symbol.items():
                    lc = last_close.get(s)
                    if lc is not None:
                        val += q * lc
                current_value = val
        
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


async def calculate_portfolio_risk_metrics(session: AsyncSession, portfolio_id: str) -> Dict:
    """
    Calculate portfolio risk metrics:
    - Annualized volatility
    - Sharpe ratio
    - Max drawdown
    - 1-day 95% Value-at-Risk (historical method)
    
    Returns None if insufficient data (< 30 daily observations)
    """
    from sqlalchemy import text
    from collections import defaultdict
    
    # Check if portfolio exists and get inception
    p_check = await session.execute(
        text("SELECT inception_date, COALESCE(initial_value,0) as initial_value FROM portfolio WHERE id = :pid"),
        {"pid": portfolio_id}
    )
    p_row = p_check.first()
    
    if not p_row:
        return None
    
    inception_date = p_row.inception_date
    initial_value = float(p_row.initial_value or 0)
    
    try:
        # Get all transactions to reconstruct daily portfolio values
        all_tx_res = await session.execute(text("""
            SELECT symbol, side, qty, price, trade_date
            FROM portfolio_transaction
            WHERE portfolio_id = :pid
            ORDER BY trade_date ASC, created_at ASC
        """), {"pid": portfolio_id})
        all_txs = [dict(r._mapping) for r in all_tx_res.fetchall()]
        
        if not all_txs:
            # No transactions = all cash, zero volatility/risk
            return {
                "volatility_annual": 0.0,
                "sharpe": None,  # Cannot calculate without returns
                "max_drawdown_pct": 0.0,
                "var_95_pct": 0.0,
                "var_95_amount": 0.0,
                "message": "No transactions - portfolio is 100% cash"
            }
        
        # Get unique symbols traded
        symbols = sorted(list({t['symbol'] for t in all_txs}))
        
        # Fetch daily prices for all symbols from inception to today
        today = date.today()
        px_res = await session.execute(text("""
            SELECT t.symbol, pd.date, pd.close
            FROM ticker t
            JOIN price_daily pd ON pd.ticker_id = t.id
            WHERE t.symbol = ANY(:symbols) AND pd.date >= :start
            ORDER BY pd.date ASC
        """), {"symbols": symbols, "start": inception_date})
        price_rows = [dict(r._mapping) for r in px_res.fetchall()]
        
        # Build prices dict: date -> symbol -> close
        prices_by_date = defaultdict(dict)
        for row in price_rows:
            prices_by_date[row['date']][row['symbol']] = float(row['close'] or 0)
        
        # Get all unique dates and sort
        all_dates = sorted(prices_by_date.keys())
        
        if len(all_dates) < 30:
            return {
                "volatility_annual": None,
                "sharpe": None,
                "max_drawdown_pct": None,
                "var_95_pct": None,
                "var_95_amount": None,
                "message": f"Insufficient data: only {len(all_dates)} trading days since inception (need ≥30)"
            }
        
        # Reconstruct daily portfolio values
        positions = defaultdict(float)
        running_cash = initial_value
        daily_values = []
        last_close_by_symbol = {}
        
        tx_by_date = defaultdict(list)
        for t in all_txs:
            tx_by_date[t['trade_date']].append(t)
        
        for d in all_dates:
            # Apply transactions for this date
            for t in tx_by_date.get(d, []):
                q = float(t['qty'] or 0)
                px = float(t['price'] or 0)
                if t['side'] == 'BUY':
                    positions[t['symbol']] += q
                    running_cash -= q * px
                elif t['side'] == 'SELL':
                    positions[t['symbol']] -= q
                    running_cash += q * px
            
            # Update last known prices
            for symbol, close_price in prices_by_date[d].items():
                last_close_by_symbol[symbol] = close_price
            
            # Calculate portfolio value
            holdings_value = sum(
                qty * last_close_by_symbol.get(symbol, 0)
                for symbol, qty in positions.items() if qty > 0
            )
            portfolio_value = running_cash + holdings_value
            daily_values.append(portfolio_value)
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(daily_values)):
            if daily_values[i-1] > 0:
                ret = (daily_values[i] - daily_values[i-1]) / daily_values[i-1]
                returns.append(ret)
        
        if len(returns) < 30:
            return {
                "volatility_annual": None,
                "sharpe": None,
                "max_drawdown_pct": None,
                "var_95_pct": None,
                "var_95_amount": None,
                "message": f"Insufficient return observations: {len(returns)} (need ≥30)"
            }
        
        returns_array = np.array(returns)
        
        # 1. Annualized Volatility
        daily_vol = np.std(returns_array, ddof=1)
        volatility_annual = daily_vol * np.sqrt(252)  # 252 trading days
        
        # 2. Sharpe Ratio
        # Fetch average risk-free rate over the same period
        rf_res = await session.execute(text("""
            SELECT AVG(rate) as avg_rate
            FROM risk_free_series
            WHERE date >= :start AND date <= :end
        """), {"start": all_dates[0], "end": all_dates[-1]})
        rf_row = rf_res.first()
        
        sharpe = None
        if rf_row and rf_row.avg_rate is not None:
            # Convert annual rate to daily
            annual_rf_rate = float(rf_row.avg_rate) / 100  # rate is stored as percentage
            daily_rf_rate = annual_rf_rate / 252
            
            # Calculate excess returns
            mean_daily_return = np.mean(returns_array)
            excess_return = mean_daily_return - daily_rf_rate
            
            # Annualized Sharpe
            if daily_vol > 0:
                sharpe = (excess_return * 252) / (daily_vol * np.sqrt(252))
        
        # 3. Max Drawdown
        peak = daily_values[0]
        max_dd = 0.0
        for value in daily_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        
        max_drawdown_pct = max_dd * 100  # As percentage
        
        # 4. 1-day 95% Historical VaR
        var_95_pct = 0.0
        var_95_amount = 0.0
        current_value = daily_values[-1]
        
        if len(returns_array) >= 50:  # Need reasonable sample for VaR
            # 5th percentile (95% confidence)
            var_threshold = np.percentile(returns_array, 5)
            var_95_pct = abs(var_threshold) * 100  # As positive percentage
            var_95_amount = abs(var_threshold * current_value)
        
        return {
            "volatility_annual": float(volatility_annual),
            "sharpe": float(sharpe) if sharpe is not None else None,
            "max_drawdown_pct": float(max_drawdown_pct),
            "var_95_pct": float(var_95_pct) if len(returns_array) >= 50 else None,
            "var_95_amount": float(var_95_amount) if len(returns_array) >= 50 else None,
            "num_observations": len(returns_array),
            "current_value": float(current_value),
            "message": "VaR requires ≥50 observations" if len(returns_array) < 50 else None
        }
    
    except Exception as e:
        logger.exception(f"Failed to calculate risk metrics: {e}")
        return {
            "volatility_annual": None,
            "sharpe": None,
            "max_drawdown_pct": None,
            "var_95_pct": None,
            "var_95_amount": None,
            "error": str(e)
        }

