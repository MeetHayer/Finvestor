# API Keys Configuration

This document lists all API keys used in the Finvestor project and where to obtain them.

## Required API Keys

### 1. FRED API Key (Risk-Free Rate Data)
**Purpose:** Fetch real 3-month Treasury Bill rates for Sharpe ratio calculation

**Current Key:** `beccf7b6140007a66bfccfe72858d4e5`

**How to Get:**
1. Go to: https://fred.stlouisfed.org/docs/api/api_key.html
2. Click "Request API Key"
3. Sign up (free)
4. Copy your key

**Configuration:**
```bash
# In backend/.env
FRED_API_KEY=beccf7b6140007a66bfccfe72858d4e5
```

**Usage:**
- Fetches daily 3-month T-Bill rates (DGS3MO series)
- Used by `backend/scripts/seed_risk_free_rate.py`
- Required for accurate Sharpe ratio calculations

---

## Optional API Keys

### 2. Alpha Vantage API Key
**Purpose:** Backup data source for stock prices (daily and intraday)

**How to Get:**
1. Go to: https://www.alphavantage.co/support/#api-key
2. Click "Get your free API key today"
3. Fill out the form
4. Copy your key

**Configuration:**
```bash
# In backend/.env
ALPHA_VANTAGE_KEY=your_key_here
# OR
ALPHAVANTAGE_KEY=your_key_here
```

**Usage:**
- Fallback for daily price data when Yahoo APIs fail
- Fallback for intraday 1-minute data
- Rate limited to 5 API requests per minute (free tier)

---

### 3. Finnhub API Key
**Purpose:** Additional backup for stock price data

**How to Get:**
1. Go to: https://finnhub.io/register
2. Sign up (free)
3. Copy API key from dashboard

**Configuration:**
```bash
# In backend/.env
FINNHUB_KEY=your_key_here
# OR
FINNHUB_API_KEY=your_key_here
```

**Usage:**
- Tertiary fallback for daily price data
- Tertiary fallback for intraday candle data
- Free tier allows 60 API calls per minute

---

## Data Source Priority

### Daily Historical Data
1. **Database** (seeded from Kaggle CSV files) - Primary
2. **yahooquery** - Secondary (no key required)
3. **yfinance** - Tertiary (no key required)
4. **Alpha Vantage** - Quaternary (requires key)
5. **Finnhub** - Quinary (requires key)

### Intraday 1-Minute Data
1. **yahooquery** - Primary (no key required)
2. **Yahoo Chart API Direct** - Secondary (no key required)
3. **Alpha Vantage** - Tertiary (requires key)

### Risk-Free Rate
1. **FRED API** - Only source (requires key, currently configured)

---

## Environment Variable Summary

```bash
# Required
FRED_API_KEY=beccf7b6140007a66bfccfe72858d4e5

# Optional (improves reliability)
ALPHA_VANTAGE_KEY=your_key_here
FINNHUB_KEY=your_key_here

# Database (required)
POSTGRES_DSN=postgresql://...
# OR
DATABASE_URL=postgresql://...
```

---

## Testing API Keys

### Test FRED API:
```bash
cd backend
source .venv/bin/activate
python scripts/seed_risk_free_rate.py
```

### Test Data Sources:
```bash
cd backend
source .venv/bin/activate
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

# Test FRED
fred_key = os.getenv('FRED_API_KEY')
print(f'FRED: {'✅' if fred_key else '❌'}')

# Test Alpha Vantage
av_key = os.getenv('ALPHA_VANTAGE_KEY') or os.getenv('ALPHAVANTAGE_KEY')
print(f'Alpha Vantage: {'✅' if av_key else '⚠️  (optional)'}')

# Test Finnhub
fh_key = os.getenv('FINNHUB_KEY') or os.getenv('FINNHUB_API_KEY')
print(f'Finnhub: {'✅' if fh_key else '⚠️  (optional)'}')
"
```

---

## Rate Limits

| Provider | Free Tier Limit | Notes |
|----------|----------------|-------|
| FRED | 120 requests/day | Very generous for our use case |
| Alpha Vantage | 5 requests/min | Can be restrictive |
| Finnhub | 60 requests/min | Better for real-time |
| Yahoo (no key) | Varies | No official limit but can rate-limit |

---

## Security Notes

- **Never commit `.env` files to Git** - they are in `.gitignore`
- API keys are **personal** - don't share them publicly
- If a key is compromised, regenerate it immediately
- Railway/Vercel deployments: Add keys as environment variables in the dashboard

---

**Last Updated:** 2025-11-19  
**Project:** Finvestor - CS 498 Senior Seminar

