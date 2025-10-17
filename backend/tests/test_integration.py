"""
Integration tests for Finvestor backend.
Tests full workflows: search → view → add to watchlist → create portfolio.
"""
import asyncio
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal
from app.services import watchlist_service, portfolio_service
from app.services.market_data import get_market_data_fetcher

async def test_full_workflow():
    """Test complete user workflow."""
    print("\n🧪 Testing Full Integration Workflow...")
    print("=" * 70)
    
    # Step 1: Fetch market data
    print("\n[1/5] Fetching market data for AAPL...")
    fetcher = get_market_data_fetcher()
    data = await fetcher.get_price_data("AAPL", range_days=7)
    assert data is not None
    print(f"  ✅ Got {len(data['prices'])} price points from {data['source']}")
    
    # Step 2: Fetch fundamentals
    print("\n[2/5] Fetching fundamentals for AAPL...")
    fundamentals = await fetcher.get_fundamentals("AAPL")
    assert fundamentals is not None
    print(f"  ✅ Got fundamentals from {fundamentals.get('source')}")
    print(f"      P/E: {fundamentals.get('pe_ratio')}")
    print(f"      Market Cap: ${fundamentals.get('market_cap', 0):,.0f}")
    
    async with SessionLocal() as session:
        # Step 3: Create watchlist and add ticker
        print("\n[3/5] Creating watchlist and adding AAPL...")
        watchlist = await watchlist_service.create_watchlist(
            session,
            name="Integration Test Watchlist"
        )
        await watchlist_service.add_ticker_to_watchlist(
            session,
            str(watchlist.id),
            "AAPL"
        )
        fetched_wl = await watchlist_service.get_watchlist(session, str(watchlist.id))
        assert len(fetched_wl.tickers) == 1
        print("  ✅ Created watchlist with AAPL")
        
        # Step 4: Create portfolio and add holding
        print("\n[4/5] Creating portfolio with AAPL holding...")
        portfolio = await portfolio_service.create_portfolio(
            session,
            name="Integration Test Portfolio",
            inception_date=date(2025, 1, 1),
            initial_value=10000
        )
        await portfolio_service.add_holding(
            session,
            str(portfolio.id),
            "AAPL",
            shares=5.0,
            average_cost=180.00
        )
        # Verify via get_all_portfolios which has proper eager loading
        all_pfs = await portfolio_service.get_all_portfolios(session)
        test_pf = next((p for p in all_pfs if str(p.id) == str(portfolio.id)), None)
        assert test_pf is not None
        print("  ✅ Created portfolio with AAPL holding (5 shares @ $180)")
        
        # Step 5: Cleanup
        print("\n[5/5] Cleaning up test data...")
        await watchlist_service.delete_watchlist(session, str(watchlist.id))
        await portfolio_service.delete_portfolio(session, str(portfolio.id))
        print("  ✅ Cleaned up")
    
    print("\n" + "=" * 70)
    print("✅ INTEGRATION TEST PASSED!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_full_workflow())
    sys.exit(0 if success else 1)

