"""
Unit tests for market data fetching.
Verifies that at least one source succeeds for AAPL and logs failure summary.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.market_data import get_market_data_fetcher


def print_separator():
    """Print a visual separator."""
    print("=" * 70)


async def test_price_data_fetch():
    """Test fetching price data for AAPL."""
    print("\n🧪 Testing Price Data Fetch for AAPL...")
    print("-" * 70)
    
    fetcher = get_market_data_fetcher()
    symbol = "AAPL"
    
    try:
        result = await fetcher.get_price_data(symbol, range_days=30)
        
        if result:
            print(f"✅ SUCCESS: Real data retrieved from [{result['source']}] for {symbol}")
            print(f"   Data points: {len(result['prices'])}")
            print(f"   Fetched at: {result['fetched_at']}")
            print(f"   Latest price: ${result['prices'][0]['close']:.2f} on {result['prices'][0]['date']}")
            return True, result['source'], None
        else:
            print(f"❌ FAILED: No data retrieved for {symbol}")
            return False, None, "All sources failed"
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False, None, str(e)


async def test_fundamentals_fetch():
    """Test fetching fundamentals for AAPL."""
    print("\n🧪 Testing Fundamentals Fetch for AAPL...")
    print("-" * 70)
    
    fetcher = get_market_data_fetcher()
    symbol = "AAPL"
    
    try:
        result = await fetcher.get_fundamentals(symbol)
        
        if result:
            print(f"✅ SUCCESS: Fundamentals retrieved from [{result.get('source', 'unknown')}] for {symbol}")
            print(f"   P/E Ratio (TTM): {result.get('pe_ratio', 'N/A')}")
            print(f"   Market Cap: ${result.get('market_cap', 0):,.0f}")
            print(f"   Beta: {result.get('beta', 'N/A')}")
            print(f"   52-Week High: ${result.get('week_52_high', 'N/A')}")
            print(f"   52-Week Low: ${result.get('week_52_low', 'N/A')}")
            return True, result.get('source'), None
        else:
            print(f"⚠️  WARNING: No fundamentals retrieved for {symbol}")
            return False, None, "All sources failed for fundamentals"
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False, None, str(e)


async def test_intraday_fetch():
    """Test fetching intraday data for AAPL."""
    print("\n🧪 Testing Intraday Data Fetch for AAPL...")
    print("-" * 70)
    
    fetcher = get_market_data_fetcher()
    symbol = "AAPL"
    
    try:
        result = await fetcher.get_intraday_data(symbol, days=1)
        
        if result:
            print(f"✅ SUCCESS: Intraday data retrieved from [{result['source']}] for {symbol}")
            print(f"   Data points: {len(result['prices'])}")
            print(f"   Interval: {result['interval']}")
            print(f"   Latest: ${result['prices'][-1]['close']:.2f} at {result['prices'][-1]['datetime']}")
            return True, result['source'], None
        else:
            print(f"⚠️  WARNING: Intraday data not available for {symbol}")
            return False, None, "Intraday not available"
            
    except Exception as e:
        print(f"⚠️  EXCEPTION: {e}")
        return False, None, str(e)


async def test_multiple_symbols():
    """Test fetching data for multiple symbols."""
    print("\n🧪 Testing Multiple Symbols...")
    print("-" * 70)
    
    fetcher = get_market_data_fetcher()
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    results = {}
    for symbol in symbols:
        try:
            result = await fetcher.get_price_data(symbol, range_days=7)
            if result:
                results[symbol] = {
                    'success': True,
                    'source': result['source'],
                    'points': len(result['prices'])
                }
                print(f"   ✓ {symbol}: {len(result['prices'])} points from {result['source']}")
            else:
                results[symbol] = {'success': False, 'error': 'No data'}
                print(f"   ✗ {symbol}: Failed")
        except Exception as e:
            results[symbol] = {'success': False, 'error': str(e)}
            print(f"   ✗ {symbol}: {e}")
        
        # Rate limiting
        await asyncio.sleep(1)
    
    success_count = sum(1 for r in results.values() if r['success'])
    print(f"\n   Summary: {success_count}/{len(symbols)} symbols succeeded")
    
    return success_count > 0, results, None


def write_test_report(results):
    """Write test results to a report file."""
    report_path = Path(__file__).parent.parent / "logs" / "fetch_report.txt"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'a') as f:
        f.write("\n" + "=" * 70 + "\n")
        f.write(f"Test Report - {datetime.now().isoformat()}\n")
        f.write("=" * 70 + "\n\n")
        
        for test_name, (success, source, error) in results.items():
            f.write(f"{test_name}:\n")
            if success:
                f.write(f"  ✅ SUCCESS (source: {source})\n")
            else:
                f.write(f"  ❌ FAILED\n")
                if error:
                    f.write(f"  Error: {error}\n")
            f.write("\n")


async def main():
    """Run all tests."""
    print_separator()
    print("🚀 Finvestor Market Data Fetch Tests")
    print_separator()
    
    results = {}
    
    # Test 1: Price data
    success, source, error = await test_price_data_fetch()
    results['Price Data (AAPL)'] = (success, source, error)
    
    # Test 2: Fundamentals
    success, source, error = await test_fundamentals_fetch()
    results['Fundamentals (AAPL)'] = (success, source, error)
    
    # Test 3: Intraday
    success, source, error = await test_intraday_fetch()
    results['Intraday (AAPL)'] = (success, source, error)
    
    # Test 4: Multiple symbols
    success, sources, error = await test_multiple_symbols()
    results['Multiple Symbols'] = (success, sources, error)
    
    # Summary
    print("\n")
    print_separator()
    print("📊 TEST SUMMARY")
    print_separator()
    
    passed = sum(1 for s, _, _ in results.values() if s)
    total = len(results)
    
    for test_name, (success, source, error) in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if error and not success:
            print(f"         Error: {error}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    print_separator()
    
    # Write report
    write_test_report(results)
    print(f"\n📝 Detailed report written to logs/fetch_report.txt")
    
    # Print failure summary if any tests failed
    if passed < total:
        print("\n⚠️  FAILURE SUMMARY:")
        print("-" * 70)
        for test_name, (success, source, error) in results.items():
            if not success:
                print(f"\n❌ {test_name}")
                print(f"   Reason: {error or 'Unknown'}")
                print(f"   All API sources failed")
                print(f"   Timestamp: {datetime.now().isoformat()}")
    
    print("\n")
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

