"""
Final audit script - Test data fetching across multiple symbols and generate report.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.market_data import get_market_data_fetcher
from app.db import SessionLocal
from sqlalchemy import select, func
from app.models import Ticker, PriceDaily, FundamentalsCache

async def audit_data_sources():
    """Test multiple symbols and report which sources succeeded."""
    print("\n" + "=" * 70)
    print("🔍 Finvestor Final Audit - Multi-Symbol Data Fetch Test")
    print("=" * 70)
    
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM", "V", "JNJ"]
    fetcher = get_market_data_fetcher()
    
    results = {
        'finnhub': [],
        'alphavantage': [],
        'yahooquery': [],
        'failed': []
    }
    
    fundamentals_results = {
        'finnhub': [],
        'alphavantage': [],
        'yahooquery': [],
        'failed': []
    }
    
    print(f"\n📊 Testing {len(symbols)} symbols...\n")
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {symbol}...")
        
        # Test price data
        try:
            price_data = await fetcher.get_price_data(symbol, range_days=30)
            if price_data:
                source = price_data['source']
                results[source].append(symbol)
                print(f"  ✅ Price data: {source} ({len(price_data['prices'])} points)")
            else:
                results['failed'].append(symbol)
                print(f"  ❌ Price data: Failed")
        except Exception as e:
            results['failed'].append(symbol)
            print(f"  ❌ Price data: {e}")
        
        # Test fundamentals
        try:
            fundamentals = await fetcher.get_fundamentals(symbol)
            if fundamentals:
                source = fundamentals.get('source', 'unknown')
                fundamentals_results[source].append(symbol)
                print(f"  ✅ Fundamentals: {source}")
            else:
                fundamentals_results['failed'].append(symbol)
                print(f"  ⚠️  Fundamentals: Not available")
        except Exception as e:
            fundamentals_results['failed'].append(symbol)
            print(f"  ❌ Fundamentals: {e}")
        
        await asyncio.sleep(1)  # Rate limiting
    
    # Database statistics
    print("\n" + "=" * 70)
    print("📊 Database Statistics")
    print("=" * 70)
    
    async with SessionLocal() as session:
        # Count tickers
        result = await session.execute(select(func.count(Ticker.id)))
        ticker_count = result.scalar()
        print(f"Total tickers in DB: {ticker_count}")
        
        # Count price rows
        result = await session.execute(select(func.count(PriceDaily.id)))
        price_count = result.scalar()
        print(f"Total price rows cached: {price_count:,}")
        
        # Count fundamentals cached
        result = await session.execute(select(func.count(FundamentalsCache.id)))
        fund_count = result.scalar()
        print(f"Fundamentals cached: {fund_count}")
    
    # Summary Report
    print("\n" + "=" * 70)
    print("📊 FINAL AUDIT REPORT")
    print("=" * 70)
    
    print("\n**Price Data Sources:**")
    print(f"  Finnhub: {len(results['finnhub'])} symbols")
    if results['finnhub']:
        print(f"    → {', '.join(results['finnhub'][:5])}{' ...' if len(results['finnhub']) > 5 else ''}")
    
    print(f"  AlphaVantage: {len(results['alphavantage'])} symbols")
    if results['alphavantage']:
        print(f"    → {', '.join(results['alphavantage'][:5])}{' ...' if len(results['alphavantage']) > 5 else ''}")
    
    print(f"  YahooQuery: {len(results['yahooquery'])} symbols")
    if results['yahooquery']:
        print(f"    → {', '.join(results['yahooquery'][:5])}{' ...' if len(results['yahooquery']) > 5 else ''}")
    
    print(f"  Failed: {len(results['failed'])} symbols")
    if results['failed']:
        print(f"    → {', '.join(results['failed'])}")
    
    print("\n**Fundamentals Sources:**")
    print(f"  Finnhub: {len(fundamentals_results['finnhub'])} symbols")
    print(f"  AlphaVantage: {len(fundamentals_results['alphavantage'])} symbols")
    print(f"  YahooQuery: {len(fundamentals_results['yahooquery'])} symbols")
    print(f"  Failed/Not Available: {len(fundamentals_results['failed'])} symbols")
    
    total_success = len(symbols) - len(results['failed'])
    success_rate = (total_success / len(symbols)) * 100
    
    print(f"\n**Overall Success Rate:** {success_rate:.1f}% ({total_success}/{len(symbols)} symbols)")
    
    async with SessionLocal() as session:
        result = await session.execute(select(func.count(PriceDaily.id)))
        price_count = result.scalar()
        print(f"**Total Price Rows Cached:** {price_count:,}")
    
    print("\n" + "=" * 70)
    
    if len(results['failed']) == 0:
        print("✅ ALL SYSTEMS OPERATIONAL")
    else:
        print(f"⚠️  {len(results['failed'])} symbols failed - check logs/fetch_report.txt")
    
    print("=" * 70 + "\n")
    
    # Write report to file
    report_path = Path(__file__).parent.parent / "logs" / "final_audit_report.txt"
    with open(report_path, 'w') as f:
        f.write(f"Finvestor Final Audit Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"="*70 + "\n\n")
        f.write(f"Symbols Tested: {len(symbols)}\n")
        f.write(f"Success Rate: {success_rate:.1f}%\n\n")
        f.write(f"Price Data Sources:\n")
        f.write(f"  Finnhub: {len(results['finnhub'])}\n")
        f.write(f"  AlphaVantage: {len(results['alphavantage'])}\n")
        f.write(f"  YahooQuery: {len(results['yahooquery'])}\n")
        f.write(f"  Failed: {len(results['failed'])}\n\n")
        f.write(f"Fundamentals Sources:\n")
        f.write(f"  Finnhub: {len(fundamentals_results['finnhub'])}\n")
        f.write(f"  AlphaVantage: {len(fundamentals_results['alphavantage'])}\n")
        f.write(f"  YahooQuery: {len(fundamentals_results['yahooquery'])}\n")
        f.write(f"  Failed: {len(fundamentals_results['failed'])}\n")
    
    print(f"📝 Full report saved to: {report_path}\n")
    
    return len(results['failed']) == 0

if __name__ == "__main__":
    success = asyncio.run(audit_data_sources())
    sys.exit(0 if success else 1)





