# Finvestor

**A complete stock portfolio management platform built for CS 498 Senior Seminar**

Finvestor helps you track your investments, analyze stock performance, and understand how your portfolio stacks up against the market. Whether you're a beginner investor or managing a serious portfolio, Finvestor gives you the tools you need to make informed decisions.

---

## What Can You Do?

### Track Any Stock
Search for any publicly traded company and see its complete price history. View interactive charts showing how the stock has performed over days, months, or years. See current prices, daily changes, and trading volume at a glance.

### Analyze with Technical Indicators
Use professional tools like moving averages, RSI, and volume analysis to understand stock trends. Toggle indicators on and off to see what they reveal about price movements. Perfect for learning how technical analysis works.

### Manage Your Portfolio
Add all your stock holdings with purchase dates and prices. Finvestor automatically calculates your portfolio's current value, tracks your gains and losses, and shows you a performance graph over time. See exactly how each investment is contributing to your overall returns.

### Compare Against the Market
One of the most important questions: "Am I beating the market?" Finvestor lets you overlay your portfolio performance against major indices like the S&P 500 (SPY), Nasdaq (QQQ), and Dow Jones (DIA). See if your stock picks are outperforming or if you'd be better off with an index fund.

### Understand Risk
Get detailed risk metrics for your portfolio:
- **Sharpe Ratio**: Are your returns worth the risk you're taking?
- **Volatility**: How much does your portfolio value swing?
- **Max Drawdown**: What's the worst loss you've experienced?
- **Value at Risk**: How much could you lose on a bad day?

These metrics help you understand not just how much you're making, but how much risk you're taking to get there.

### Monitor Intraday Movements
Watch stocks move minute-by-minute with 1-minute candlestick charts. See how prices react to news, earnings, or market events in real-time. Charts automatically refresh every 60 seconds so you always have the latest data.

### Build Watchlists
Keep track of stocks you're interested in but haven't bought yet. Create multiple watchlists for different strategies or sectors. See all your watched stocks' prices and changes in one place.

### Learn as You Go
The Methods page explains how all the technical indicators and risk metrics work. Understand what moving averages actually measure, why the Sharpe ratio matters, and how to interpret volatility. No finance degree required.

---

## Key Features

**Stock Analysis**
- Real-time and historical price data for thousands of stocks
- Interactive candlestick and line charts
- Company fundamentals (P/E ratio, market cap, beta)
- 52-week high and low ranges
- Trading volume analysis

**Portfolio Management**
- Track multiple portfolios
- Add holdings with purchase dates and prices
- Automatic cost basis calculation
- Real-time portfolio valuation
- Performance graphs showing value over time
- Individual holding performance breakdown

**Risk Analysis**
- Annualized volatility calculation
- Sharpe ratio using real risk-free rates from the Federal Reserve
- Maximum drawdown analysis
- Value at Risk (VaR) estimates
- Detailed explanations of what each metric means

**Technical Analysis**
- Simple Moving Average (SMA)
- Exponential Moving Average (EMA)
- Relative Strength Index (RSI)
- Customizable indicator periods
- Visual overlays on price charts

**Benchmark Comparison**
- Compare portfolio returns against SPY, QQQ, and DIA
- See how your investments performed relative to the market
- Visual overlays on performance graphs
- Same starting date comparison for fair evaluation

**Intraday Trading**
- 1-minute candlestick charts
- Last 7 days of minute-by-minute data
- Auto-refresh every 60 seconds
- Perfect for day trading or monitoring real-time movements

**Watchlists**
- Create unlimited watchlists
- Track stocks you're considering
- Quick access to favorite companies
- Real-time price updates

---

## Getting Started

### Prerequisites
- Python 3.11 or higher
- PostgreSQL 14 or higher
- Node.js 18 or higher

### Installation

**1. Clone the repository**
```bash
git clone <repository-url>
cd finvestor
```

**2. Set up the backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend` directory:
```env
POSTGRES_DSN=postgresql+asyncpg://username:password@localhost:5432/dbname
FRED_API_KEY=your_fred_api_key_here  # Optional but recommended for Sharpe ratio
```

Run database migrations:
```bash
alembic upgrade head
```

Seed risk-free rate data (for Sharpe ratio calculations):
```bash
python3 scripts/seed_risk_free_rate.py
```

Start the backend server:
```bash
uvicorn app.main:app --reload --port 8000
```

**3. Set up the frontend**

```bash
cd frontend
npm install
```

Create a `.env` file in the `frontend` directory:
```env
VITE_API_BASE=http://localhost:8000
```

Start the development server:
```bash
npm run dev
```

**4. Open the application**

Navigate to http://localhost:5173 in your browser.

The API documentation is available at http://localhost:8000/docs

---

## How It Works

### Data Sources
Finvestor pulls stock data from multiple reliable sources to ensure accuracy and availability:
- **Yahoo Finance APIs** (yahooquery, yfinance) - Primary source for prices and company data
- **Alpha Vantage** - Backup for historical prices and fundamentals
- **Finnhub** - Company profiles and financial metrics
- **FRED (Federal Reserve)** - Risk-free rates for Sharpe ratio calculations

If one source is unavailable, the system automatically falls back to others.

### Portfolio Tracking
When you add a holding, Finvestor:
1. Fetches the historical price for your purchase date
2. Calculates your cost basis (price × quantity)
3. Updates your cash balance
4. Recalculates your portfolio value using current prices
5. Updates your performance graph

All calculations happen in real-time as you add or remove holdings.

### Risk Metrics
Risk metrics are calculated from your portfolio's daily value history:
- **Volatility**: Standard deviation of daily returns, annualized
- **Sharpe Ratio**: (Portfolio Return - Risk-Free Rate) / Volatility
- **Max Drawdown**: Largest peak-to-trough decline percentage
- **VaR**: 95th percentile of worst daily returns

The system uses real 3-month Treasury Bill rates from the Federal Reserve for accurate Sharpe ratio calculations.

---

## Project Structure

```
finvestor/
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── services/       # Business logic and data fetching
│   │   └── models.py       # Database models
│   ├── alembic/           # Database migrations
│   ├── scripts/           # Utility scripts (seeding, etc.)
│   └── requirements.txt   # Python dependencies
│
├── frontend/               # React frontend
│   ├── src/
│   │   ├── routes/        # Page components
│   │   ├── components/    # Reusable UI components
│   │   ├── hooks/         # React hooks for data fetching
│   │   └── lib/           # Utilities and API client
│   └── package.json       # Node dependencies
│
└── docs/                  # Documentation
```

---

## Development Journey

This project was built over four checkpoints, each adding significant functionality:

**Checkpoint #1** - Built the foundation with PostgreSQL database, seeded initial stock data, and created the core API endpoints.

**Checkpoint #2** - Developed the React frontend, implemented watchlist and portfolio management, and created interactive charts.

**Checkpoint #3** - Added live market benchmarks, improved data reliability with multiple API sources, and polished the user experience.

**Checkpoint #4** - Implemented advanced analytics including risk metrics (Sharpe ratio, VaR, volatility, max drawdown), 1-minute intraday charts, benchmark comparisons, and comprehensive educational content.

---

## Technology Stack

**Backend**
- FastAPI - Modern Python web framework
- PostgreSQL - Relational database
- SQLAlchemy - Database ORM
- Alembic - Database migrations

**Frontend**
- React - UI framework
- Vite - Build tool
- Tailwind CSS - Styling
- ECharts - Charting library
- React Query - Data fetching and caching

**Data Sources**
- Yahoo Finance (multiple APIs)
- Alpha Vantage
- Finnhub
- FRED (Federal Reserve Economic Data)

---

## Documentation

For detailed information, see the `docs/` directory:
- **Setup Guide** - Complete installation instructions
- **User Guide** - How to use all features
- **API Keys** - How to obtain and configure API keys
- **Changelog** - Detailed history of changes

---

## Important Notes

This is an educational project created for CS 498 Senior Seminar. While it uses real stock data, it is not intended as financial advice. Always consult with qualified financial professionals before making investment decisions.

The application is designed to help you learn about investing, understand portfolio management, and practice using real market data. Use it as a tool for education and practice, not as your sole source of investment guidance.

---

## License

This project is created for educational purposes as part of CS 498 Senior Seminar.

---

**Built by Manmeet S Hayer**  
**CS 498 - Senior Seminar**  
**Checkpoint #4 Complete** ✅
