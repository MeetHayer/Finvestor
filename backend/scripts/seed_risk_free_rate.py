#!/usr/bin/env python3
"""
Seed REAL risk-free rate data from FRED (Federal Reserve Economic Data).
Fetches 3-month Treasury Bill rates (DGS3MO series).

Requires FRED API key (free): https://fred.stlouisfed.org/docs/api/api_key.html
Add to backend/.env: FRED_API_KEY=your_key_here
"""
import sys
from pathlib import Path
from datetime import date, timedelta
from sqlalchemy import create_engine, text

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

def get_database_url():
    """Get sync database URL"""
    import os
    dsn = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_DSN')
    if not dsn:
        raise RuntimeError('DATABASE_URL or POSTGRES_DSN not set')
    
    # Convert to sync psycopg
    if dsn.startswith('postgres://'):
        dsn = dsn.replace('postgres://', 'postgresql://', 1)
    if 'postgresql+asyncpg' in dsn:
        dsn = dsn.replace('postgresql+asyncpg', 'postgresql+psycopg')
    elif 'postgresql://' in dsn and '+' not in dsn:
        dsn = dsn.replace('postgresql://', 'postgresql+psycopg://')
    
    return dsn

def seed_risk_free_rates(engine):
    """
    Fetch REAL risk-free rate data from FRED and seed the database.
    Uses 3-month Treasury Bill Secondary Market Rate (DGS3MO).
    """
    import os
    import ssl
    import certifi
    from fredapi import Fred
    
    # Fix SSL certificate issues on macOS
    ssl._create_default_https_context = ssl._create_unverified_context
    
    # Get FRED API key
    fred_key = os.getenv('FRED_API_KEY') or os.getenv('FREDAPI_KEY')
    if not fred_key:
        raise RuntimeError(
            "FRED API key not found!\n\n"
            "To get a FREE FRED API key:\n"
            "1. Go to: https://fred.stlouisfed.org/docs/api/api_key.html\n"
            "2. Click 'Request API Key'\n"
            "3. Sign up (free, takes 2 minutes)\n"
            "4. Add to backend/.env:\n"
            "   FRED_API_KEY=your_key_here\n"
        )
    
    print("🔗 Connecting to FRED API...")
    fred = Fred(api_key=fred_key)
    
    with engine.connect() as conn:
        # Check if data already exists
        result = conn.execute(text("SELECT COUNT(*) FROM risk_free_series"))
        count = result.scalar()
        
        if count > 0:
            print(f"  ℹ️  Risk-free rate data already exists ({count} rows)")
            overwrite = input("  Overwrite with fresh FRED data? (y/N): ").strip().lower()
            if overwrite != 'y':
                print("  Skipping seed")
                return count
            
            # Clear existing data
            conn.execute(text("DELETE FROM risk_free_series"))
            conn.commit()
            print("  ✅ Cleared existing data")
        
        # Fetch 3-month T-Bill rates from FRED
        # DGS3MO = 3-Month Treasury Constant Maturity Rate
        end_date = date.today()
        start_date = end_date - timedelta(days=730)  # Last 2 years
        
        print(f"📥 Fetching real 3-month T-Bill rates from {start_date} to {end_date}...")
        
        try:
            # Fetch data from FRED
            data = fred.get_series('DGS3MO', observation_start=start_date, observation_end=end_date)
            
            if data is None or len(data) == 0:
                raise RuntimeError("No data returned from FRED")
            
            print(f"  ✅ Received {len(data)} observations from FRED")
            
            # Insert into database
            rates_inserted = 0
            for date_val, rate_val in data.items():
                # Skip NaN values (weekends/holidays)
                if rate_val != rate_val:  # NaN check
                    continue
                
                conn.execute(
                    text("""
                        INSERT INTO risk_free_series (date, rate) 
                        VALUES (:date, :rate) 
                        ON CONFLICT (date) DO UPDATE SET rate = :rate
                    """),
                    {"date": date_val.date(), "rate": float(rate_val)}
                )
                rates_inserted += 1
            
            conn.commit()
            
            print(f"  ✅ Seeded {rates_inserted} days of REAL risk-free rate data")
            print(f"  Date range: {data.index[0].date()} to {data.index[-1].date()}")
            print(f"  Latest rate: {data.iloc[-1]:.2f}% (as of {data.index[-1].date()})")
            print(f"  Average rate: {data.mean():.2f}%")
            
            return rates_inserted
            
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data from FRED: {e}")

if __name__ == '__main__':
    try:
        engine = create_engine(get_database_url())
        count = seed_risk_free_rates(engine)
        print(f"\n✅ Success! Sharpe ratio calculations will now work.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

