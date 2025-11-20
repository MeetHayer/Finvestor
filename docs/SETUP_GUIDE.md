# 🚀 Finvestor Setup Guide

Complete guide to setting up and running Finvestor locally.

---

## Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **PostgreSQL** 14+
- **Git**

---

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd finvestor
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

**Edit `backend/.env` with your configuration:**

```env
# Database
POSTGRES_DSN=postgresql+asyncpg://finvestor:finvestor1234@localhost:5432/sampleStocksData

# API Keys (Optional but recommended)
FRED_API_KEY=your_fred_api_key_here
ALPHA_VANTAGE_KEY=your_alphavantage_key_here
FINNHUB_KEY=your_finnhub_key_here
```

**Run database migrations:**

```bash
alembic upgrade head
```

**Seed risk-free rate data (for Sharpe ratio):**

```bash
python3 scripts/seed_risk_free_rate.py
```

**Start backend:**

```bash
uvicorn app.main:app --reload --port 8000
```

Backend will be available at: http://localhost:8000

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
```

**Edit `frontend/.env`:**

```env
VITE_API_BASE=http://localhost:8000
```

**Start frontend:**

```bash
npm run dev
```

Frontend will be available at: http://localhost:5173

---

## API Keys Configuration

See [API_KEYS.md](./API_KEYS.md) for detailed information on obtaining and configuring API keys.

### Required Keys

- **FRED_API_KEY**: For risk-free rate data (Sharpe ratio calculations)
  - Get it free at: https://fred.stlouisfed.org/docs/api/api_key.html

### Optional Keys (Improve data reliability)

- **ALPHA_VANTAGE_KEY**: Backup for stock data
  - Get it free at: https://www.alphavantage.co/support/#api-key

- **FINNHUB_KEY**: Company fundamentals
  - Get it free at: https://finnhub.io/register

---

## Database Setup

### Local PostgreSQL

**Create database:**

```bash
psql -U postgres
CREATE DATABASE sampleStocksData;
CREATE USER finvestor WITH PASSWORD 'finvestor1234';
GRANT ALL PRIVILEGES ON DATABASE sampleStocksData TO finvestor;
\q
```

**Run migrations:**

```bash
cd backend
alembic upgrade head
```

### Seeding Data

The application will automatically fetch and cache stock data from Yahoo Finance APIs when you first search for a ticker. No manual seeding required!

---

## Troubleshooting

### Backend won't start

**Error: "DATABASE_URL not set"**
- Check that `POSTGRES_DSN` is set in `backend/.env`
- Verify PostgreSQL is running: `pg_isready`

**Error: "Module not found"**
- Activate virtual environment: `source .venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### Frontend won't start

**Error: "Cannot connect to backend"**
- Check backend is running on port 8000
- Verify `VITE_API_BASE` in `frontend/.env`

**Error: "CORS error"**
- Backend must be running on http://localhost:8000
- Frontend must be running on http://localhost:5173

### Data not loading

**Prices not showing:**
- Check browser console for API errors
- Verify backend logs for Yahoo API rate limits
- Try refreshing the page

**Sharpe ratio showing N/A:**
- Run: `python3 backend/scripts/seed_risk_free_rate.py`
- Check that FRED_API_KEY is set in backend/.env

---

## Development Tips

### Hot Reload

Both frontend and backend support hot reload:
- Backend: `--reload` flag automatically reloads on code changes
- Frontend: Vite automatically reloads on file changes

### Viewing Logs

**Backend logs:**
```bash
# In backend terminal, logs appear automatically
# Look for lines starting with INFO, WARNING, ERROR
```

**Frontend logs:**
```bash
# Open browser DevTools (F12)
# Check Console tab for API requests and errors
```

### Database Queries

**View data directly:**
```bash
psql -U finvestor -d sampleStocksData
\dt  # List tables
SELECT * FROM ticker LIMIT 10;
SELECT * FROM portfolio;
```

---

## Next Steps

- Read [USER_GUIDE.md](./USER_GUIDE.md) to learn how to use Finvestor
- Check [CHANGELOG.md](./CHANGELOG.md) for recent updates
- See [FINVESTOR_DOCUMENTATION.md](./FINVESTOR_DOCUMENTATION.md) for comprehensive technical documentation

---

**Need Help?** Check the troubleshooting section above or review the detailed documentation.

