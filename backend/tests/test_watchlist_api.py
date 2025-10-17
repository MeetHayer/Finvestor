"""
Tests for watchlist API endpoints.
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal
from app.services import watchlist_service

async def test_watchlist_crud():
    """Test complete watchlist CRUD operations."""
    print("\n🧪 Testing Watchlist CRUD...")
    print("-" * 70)
    
    async with SessionLocal() as session:
        # Create watchlist
        print("  Creating watchlist...")
        watchlist = await watchlist_service.create_watchlist(
            session,
            name="Test Watchlist",
            description="Test description"
        )
        assert watchlist is not None
        assert watchlist.name == "Test Watchlist"
        print(f"  ✅ Created watchlist: {watchlist.id}")
        
        # Add ticker
        print("  Adding AAPL to watchlist...")
        success = await watchlist_service.add_ticker_to_watchlist(
            session,
            str(watchlist.id),
            "AAPL"
        )
        assert success
        print("  ✅ Added AAPL")
        
        # Get watchlist
        print("  Fetching watchlist...")
        fetched = await watchlist_service.get_watchlist(session, str(watchlist.id))
        assert fetched is not None
        assert len(fetched.tickers) == 1
        assert fetched.tickers[0].symbol == "AAPL"
        print(f"  ✅ Fetched watchlist with {len(fetched.tickers)} ticker(s)")
        
        # Remove ticker
        print("  Removing AAPL...")
        success = await watchlist_service.remove_ticker_from_watchlist(
            session,
            str(watchlist.id),
            "AAPL"
        )
        assert success
        print("  ✅ Removed AAPL")
        
        # Delete watchlist
        print("  Deleting watchlist...")
        success = await watchlist_service.delete_watchlist(session, str(watchlist.id))
        assert success
        print("  ✅ Deleted watchlist")
    
    print("\n✅ All watchlist tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_watchlist_crud())
    sys.exit(0 if success else 1)





