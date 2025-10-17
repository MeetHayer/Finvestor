"""
Watchlist management service for Finvestor.
"""
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Watchlist, Ticker, watchlist_tickers

logger = logging.getLogger(__name__)


async def create_watchlist(
    session: AsyncSession,
    name: str,
    description: Optional[str] = None
) -> Watchlist:
    """
    Create a new watchlist.
    
    Args:
        session: Database session
        name: Watchlist name
        description: Optional description
        
    Returns:
        Created watchlist
    """
    try:
        watchlist = Watchlist(
            name=name,
            description=description
        )
        session.add(watchlist)
        await session.commit()
        await session.refresh(watchlist)
        
        logger.info(f"Created watchlist: {name} (ID: {watchlist.id})")
        return watchlist
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating watchlist {name}: {e}")
        raise


async def get_all_watchlists(session: AsyncSession) -> List[Watchlist]:
    """
    Get all watchlists with their tickers.
    
    Args:
        session: Database session
        
    Returns:
        List of watchlists
    """
    try:
        result = await session.execute(
            select(Watchlist)
            .options(selectinload(Watchlist.tickers))
            .order_by(Watchlist.created_at.desc())
        )
        watchlists = result.scalars().all()
        return list(watchlists)
    except Exception as e:
        logger.error(f"Error fetching watchlists: {e}")
        return []


async def get_watchlist(session: AsyncSession, watchlist_id: str) -> Optional[Watchlist]:
    """
    Get a specific watchlist by ID.
    
    Args:
        session: Database session
        watchlist_id: Watchlist UUID
        
    Returns:
        Watchlist or None
    """
    try:
        result = await session.execute(
            select(Watchlist)
            .options(selectinload(Watchlist.tickers))
            .where(Watchlist.id == watchlist_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error fetching watchlist {watchlist_id}: {e}")
        return None


async def add_ticker_to_watchlist(
    session: AsyncSession,
    watchlist_id: str,
    symbol: str
) -> bool:
    """
    Add a ticker to a watchlist.
    
    Args:
        session: Database session
        watchlist_id: Watchlist UUID
        symbol: Ticker symbol
        
    Returns:
        True if successful
    """
    try:
        # Get watchlist
        watchlist = await get_watchlist(session, watchlist_id)
        if not watchlist:
            logger.warning(f"Watchlist {watchlist_id} not found")
            return False
        
        # Get or create ticker
        result = await session.execute(
            select(Ticker).where(Ticker.symbol == symbol.upper())
        )
        ticker = result.scalar_one_or_none()
        
        if not ticker:
            # Create ticker if it doesn't exist
            ticker = Ticker(symbol=symbol.upper(), name=symbol.upper())
            session.add(ticker)
            await session.commit()
            await session.refresh(ticker)
        
        # Add to watchlist if not already there
        if ticker not in watchlist.tickers:
            watchlist.tickers.append(ticker)
            watchlist.updated_at = datetime.now()
            await session.commit()
            logger.info(f"Added {symbol} to watchlist {watchlist.name}")
        
        return True
    except Exception as e:
        await session.rollback()
        logger.error(f"Error adding {symbol} to watchlist {watchlist_id}: {e}")
        return False


async def remove_ticker_from_watchlist(
    session: AsyncSession,
    watchlist_id: str,
    symbol: str
) -> bool:
    """
    Remove a ticker from a watchlist.
    
    Args:
        session: Database session
        watchlist_id: Watchlist UUID
        symbol: Ticker symbol
        
    Returns:
        True if successful
    """
    try:
        watchlist = await get_watchlist(session, watchlist_id)
        if not watchlist:
            return False
        
        result = await session.execute(
            select(Ticker).where(Ticker.symbol == symbol.upper())
        )
        ticker = result.scalar_one_or_none()
        
        if ticker and ticker in watchlist.tickers:
            watchlist.tickers.remove(ticker)
            watchlist.updated_at = datetime.now()
            await session.commit()
            logger.info(f"Removed {symbol} from watchlist {watchlist.name}")
        
        return True
    except Exception as e:
        await session.rollback()
        logger.error(f"Error removing {symbol} from watchlist {watchlist_id}: {e}")
        return False


async def delete_watchlist(session: AsyncSession, watchlist_id: str) -> bool:
    """
    Delete a watchlist.
    
    Args:
        session: Database session
        watchlist_id: Watchlist UUID
        
    Returns:
        True if successful
    """
    try:
        watchlist = await get_watchlist(session, watchlist_id)
        if not watchlist:
            return False
        
        await session.delete(watchlist)
        await session.commit()
        logger.info(f"Deleted watchlist {watchlist_id}")
        return True
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting watchlist {watchlist_id}: {e}")
        return False

