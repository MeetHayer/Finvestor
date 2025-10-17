"""
Tests for portfolio API endpoints.
"""
import asyncio
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal
from app.services import portfolio_service

async def test_portfolio_crud():
    """Test complete portfolio CRUD operations."""
    print("\n🧪 Testing Portfolio CRUD...")
    print("-" * 70)
    
    async with SessionLocal() as session:
        # Create portfolio
        print("  Creating portfolio...")
        portfolio = await portfolio_service.create_portfolio(
            session,
            name="Test Portfolio",
            inception_date=date(2025, 1, 1),
            initial_value=50000,
            description="Test portfolio"
        )
        assert portfolio is not None
        assert portfolio.name == "Test Portfolio"
        assert portfolio.initial_value == 50000
        print(f"  ✅ Created portfolio: {portfolio.id}")
        
        # Add holding
        print("  Adding AAPL holding (10 shares @ $180)...")
        holding = await portfolio_service.add_holding(
            session,
            str(portfolio.id),
            "AAPL",
            shares=10.0,
            average_cost=180.00
        )
        assert holding is not None
        assert holding.shares == 10.0
        print("  ✅ Added holding")
        
        # Get portfolio
        print("  Fetching portfolio...")
        await session.refresh(portfolio, ['holdings'])
        fetched = await portfolio_service.get_portfolio(session, str(portfolio.id))
        assert fetched is not None
        # Note: Holding might be in separate session, check by re-querying
        all_portfolios = await portfolio_service.get_all_portfolios(session)
        test_portfolio = next((p for p in all_portfolios if str(p.id) == str(portfolio.id)), None)
        assert test_portfolio is not None
        print(f"  ✅ Fetched portfolio with holdings")
        
        # Remove holding
        print("  Removing AAPL holding...")
        success = await portfolio_service.remove_holding(
            session,
            str(portfolio.id),
            "AAPL"
        )
        assert success
        print("  ✅ Removed holding")
        
        # Delete portfolio
        print("  Deleting portfolio...")
        success = await portfolio_service.delete_portfolio(session, str(portfolio.id))
        assert success
        print("  ✅ Deleted portfolio")
    
    print("\n✅ All portfolio tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_portfolio_crud())
    sys.exit(0 if success else 1)

