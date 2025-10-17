"""
Portfolio management service for Finvestor.
"""
import logging
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Portfolio, PortfolioHolding, Ticker

logger = logging.getLogger(__name__)


async def create_portfolio(
    session: AsyncSession,
    name: str,
    inception_date: date,
    initial_value: float = 0,
    description: Optional[str] = None
) -> Portfolio:
    """
    Create a new portfolio.
    
    Args:
        session: Database session
        name: Portfolio name
        inception_date: Start date
        initial_value: Initial capital
        description: Optional description
        
    Returns:
        Created portfolio
    """
    try:
        portfolio = Portfolio(
            name=name,
            description=description,
            inception_date=inception_date,
            initial_value=Decimal(str(initial_value))
        )
        session.add(portfolio)
        await session.commit()
        await session.refresh(portfolio)
        
        logger.info(f"Created portfolio: {name} (ID: {portfolio.id})")
        return portfolio
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating portfolio {name}: {e}")
        raise


async def get_all_portfolios(session: AsyncSession) -> List[Portfolio]:
    """
    Get all portfolios with their holdings.
    
    Args:
        session: Database session
        
    Returns:
        List of portfolios
    """
    try:
        result = await session.execute(
            select(Portfolio)
            .options(selectinload(Portfolio.holdings))
            .order_by(Portfolio.created_at.desc())
        )
        portfolios = result.scalars().all()
        return list(portfolios)
    except Exception as e:
        logger.error(f"Error fetching portfolios: {e}")
        return []


async def get_portfolio(
    session: AsyncSession,
    portfolio_id: str
) -> Optional[Portfolio]:
    """
    Get a specific portfolio by ID.
    
    Args:
        session: Database session
        portfolio_id: Portfolio UUID
        
    Returns:
        Portfolio or None
    """
    try:
        result = await session.execute(
            select(Portfolio)
            .options(selectinload(Portfolio.holdings).selectinload(PortfolioHolding.ticker))
            .where(Portfolio.id == portfolio_id)
        )
        await session.commit()  # Ensure session is synchronized
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error fetching portfolio {portfolio_id}: {e}")
        return None


async def add_holding(
    session: AsyncSession,
    portfolio_id: str,
    symbol: str,
    shares: float,
    average_cost: Optional[float] = None
) -> Optional[PortfolioHolding]:
    """
    Add or update a holding in a portfolio.
    
    Args:
        session: Database session
        portfolio_id: Portfolio UUID
        symbol: Ticker symbol
        shares: Number of shares
        average_cost: Average cost per share
        
    Returns:
        Created/updated holding or None
    """
    try:
        # Validate portfolio exists
        portfolio = await get_portfolio(session, portfolio_id)
        if not portfolio:
            logger.warning(f"Portfolio {portfolio_id} not found")
            return None
        
        # Get or create ticker
        result = await session.execute(
            select(Ticker).where(Ticker.symbol == symbol.upper())
        )
        ticker = result.scalar_one_or_none()
        
        if not ticker:
            ticker = Ticker(symbol=symbol.upper(), name=symbol.upper())
            session.add(ticker)
            await session.commit()
            await session.refresh(ticker)
        
        # Check if holding already exists
        result = await session.execute(
            select(PortfolioHolding).where(
                PortfolioHolding.portfolio_id == portfolio_id,
                PortfolioHolding.ticker_id == ticker.id
            )
        )
        holding = result.scalar_one_or_none()
        
        if holding:
            # Update existing holding
            holding.shares = Decimal(str(shares))
            if average_cost is not None:
                holding.average_cost = Decimal(str(average_cost))
        else:
            # Create new holding
            holding = PortfolioHolding(
                portfolio_id=portfolio_id,
                ticker_id=ticker.id,
                shares=Decimal(str(shares)),
                average_cost=Decimal(str(average_cost)) if average_cost else None
            )
            session.add(holding)
        
        portfolio.updated_at = datetime.now()
        await session.commit()
        await session.refresh(holding)
        
        logger.info(f"Added/updated holding: {shares} shares of {symbol} in portfolio {portfolio.name}")
        return holding
    except Exception as e:
        await session.rollback()
        logger.error(f"Error adding holding to portfolio {portfolio_id}: {e}")
        return None


async def remove_holding(
    session: AsyncSession,
    portfolio_id: str,
    symbol: str
) -> bool:
    """
    Remove a holding from a portfolio.
    
    Args:
        session: Database session
        portfolio_id: Portfolio UUID
        symbol: Ticker symbol
        
    Returns:
        True if successful
    """
    try:
        # Get ticker
        result = await session.execute(
            select(Ticker).where(Ticker.symbol == symbol.upper())
        )
        ticker = result.scalar_one_or_none()
        
        if not ticker:
            return False
        
        # Find and delete holding
        result = await session.execute(
            select(PortfolioHolding).where(
                PortfolioHolding.portfolio_id == portfolio_id,
                PortfolioHolding.ticker_id == ticker.id
            )
        )
        holding = result.scalar_one_or_none()
        
        if holding:
            await session.delete(holding)
            
            # Update portfolio timestamp
            portfolio = await get_portfolio(session, portfolio_id)
            if portfolio:
                portfolio.updated_at = datetime.now()
            
            await session.commit()
            logger.info(f"Removed {symbol} from portfolio {portfolio_id}")
            return True
        
        return False
    except Exception as e:
        await session.rollback()
        logger.error(f"Error removing holding from portfolio {portfolio_id}: {e}")
        return False


async def delete_portfolio(session: AsyncSession, portfolio_id: str) -> bool:
    """
    Delete a portfolio and all its holdings.
    
    Args:
        session: Database session
        portfolio_id: Portfolio UUID
        
    Returns:
        True if successful
    """
    try:
        portfolio = await get_portfolio(session, portfolio_id)
        if not portfolio:
            return False
        
        await session.delete(portfolio)
        await session.commit()
        logger.info(f"Deleted portfolio {portfolio_id}")
        return True
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting portfolio {portfolio_id}: {e}")
        return False

