# Finvestor - Your Personal Stock Portfolio Manager

**CS 498 - Senior Seminar Project**  
**Author**: Manmeet S Hayer  
**Status**: Checkpoint #3 Complete ✅

---

## 🎯 What is Finvestor?

Finvestor is a web-based stock portfolio management platform that helps you track, analyze, and optimize your investments. Get real-time stock prices, view technical indicators, manage your watchlists, and monitor your portfolio performance - all in one place.

---

## ✨ What You Can Do

### 📈 Track Stock Prices & Charts
- **Real-time market data** for thousands of stocks
- **Interactive candlestick charts** showing price movements over time
- **Volume indicators** to see trading activity
- **Historical data** with up to 5 years of price history
- **Multiple timeframes** - view daily, weekly, or monthly trends

### 📊 View Technical Indicators
- **Moving averages** to identify trends
- **Support and resistance levels** to spot key price points
- **Volume analysis** to gauge market interest
- **Price change indicators** showing daily gains/losses
- **52-week high/low** to understand stock ranges

### 🎯 Monitor Market Benchmarks
- **Live index tracking** - SPY (S&P 500), QQQ (Nasdaq), DIA (Dow Jones)
- **Real-time price updates** throughout the trading day
- **Daily change percentages** to see market direction
- **Compare your portfolio** against major indexes

### 👀 Create Custom Watchlists
- **Track your favorite stocks** in one place
- **Quick access** to companies you're interested in
- **Add and remove stocks** with a single click
- **Search thousands of tickers** with autocomplete
- **See real-time prices** for all your watched stocks

### 💼 Manage Your Portfolio
- **Track all your holdings** with purchase dates and quantities
- **Automatic price updates** from historical data
- **Portfolio value tracking** with real-time calculations
- **See your gains and losses** at a glance
- **Detailed breakdown** of each investment
- **Performance metrics** showing how your portfolio is doing

### 📱 Stock Fundamentals
- **P/E Ratio** (Price-to-Earnings) - Is the stock overvalued?
- **Market Cap** - How big is the company?
- **Beta** - How volatile is the stock compared to the market?
- **52-Week Range** - What's the stock's yearly high and low?
- **Trading Volume** - How actively is it being traded?

### 🔍 Smart Search
- **Instant search** across all available stocks
- **Ticker symbol search** (e.g., AAPL, MSFT, TSLA)
- **Company name search** (e.g., "Apple", "Microsoft")
- **Fast autocomplete** as you type
- **Recent searches** for quick access

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Node.js 18+

### Start the Backend
```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt  # First time only
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start the Frontend
```bash
cd frontend
npm install  # First time only
npm run dev
```

### Open the App
- **Finvestor App**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs

---

## 💡 How to Use Finvestor

### 1. Browse Market Benchmarks
When you first open Finvestor, you'll see the major market indexes (SPY, QQQ, DIA) with live prices and daily changes. This gives you a quick snapshot of overall market direction.

### 2. Search for Stocks
Use the search bar to find any stock by ticker symbol (like "AAPL" for Apple) or company name. You'll get instant results with autocomplete suggestions.

### 3. View Stock Details
Click on any stock to see:
- Interactive price charts with candlesticks
- Trading volume over time
- Key fundamentals (P/E ratio, market cap, etc.)
- 52-week high/low ranges
- Current price and daily change

### 4. Build Your Watchlist
Found stocks you're interested in? Add them to your watchlist with one click. Your watchlist gives you quick access to monitor all your favorite stocks in one place.

### 5. Track Your Portfolio
Add your actual stock holdings to track your investments:
- Enter the ticker symbol
- Add the quantity you own
- Specify when you bought it
- Finvestor automatically pulls the historical price
- See your portfolio value update in real-time

### 6. Analyze Performance
Check your portfolio page to see:
- Total portfolio value
- Individual holding performance
- Gains and losses
- Asset allocation breakdown
- How you're performing vs. market indexes

---

## 📊 Sample Stocks Available

Finvestor comes pre-loaded with price data for popular stocks across major sectors:

- **Tech**: Apple (AAPL), Microsoft (MSFT), Google (GOOGL), Tesla (TSLA)
- **Finance**: JPMorgan (JPM), Bank of America (BAC), Goldman Sachs (GS)
- **Retail**: Amazon (AMZN), Walmart (WMT), Target (TGT)
- **Healthcare**: Johnson & Johnson (JNJ), Pfizer (PFE), UnitedHealth (UNH)
- **Energy**: ExxonMobil (XOM), Chevron (CVX)
- **And many more...**

---

## 🎨 Beautiful, Responsive Design

### Desktop Experience
- **Full-width charts** for detailed analysis
- **Side-by-side layouts** for easy comparison
- **Smooth animations** for a polished feel
- **Dark theme support** for comfortable viewing

### Mobile Experience
- **Responsive charts** that adapt to small screens
- **Touch-friendly buttons** and controls
- **Hamburger menu** for easy navigation
- **Optimized layouts** for phones and tablets

---

## 📱 Key Features at a Glance

| Feature | Description |
|---------|-------------|
| 📈 **Real-Time Data** | Live stock prices and market updates |
| 📊 **Interactive Charts** | Candlestick charts with volume indicators |
| 🎯 **Watchlists** | Track your favorite stocks |
| 💼 **Portfolio Tracking** | Monitor your actual investments |
| 🔍 **Smart Search** | Find any stock instantly |
| 📉 **Technical Indicators** | Moving averages, volume, trends |
| 🏦 **Market Benchmarks** | SPY, QQQ, DIA tracking |
| 📱 **Mobile Friendly** | Works on any device |
| 🎨 **Modern UI** | Clean, professional design |
| ⚡ **Fast Performance** | Optimized for speed |

---

## 📈 Data Sources

Finvestor pulls stock data from multiple reliable sources:
- **Finnhub** - Real-time market data
- **AlphaVantage** - Historical prices and fundamentals
- **YahooQuery** - Company information and metrics
- **yahoo_fin** - Live index data and current prices

This multi-source approach ensures you always get accurate, up-to-date information.

---

## 🛠️ Built With

**Backend:**
- FastAPI (Python) - High-performance API server
- PostgreSQL - Reliable database for stock data
- SQLAlchemy - Database operations

**Frontend:**
- React - Modern, responsive user interface
- Tailwind CSS - Beautiful styling
- ECharts - Professional financial charts
- React Query - Smart data caching

---

## 🎯 Checkpoint Progress

### ✅ Checkpoint #1 - Database & API Foundation
- Set up PostgreSQL database with stock data
- Created API endpoints for data access
- Seeded 25 stocks with 5 years of history
- Established data relationships

### ✅ Checkpoint #2 - User Interface & Core Features
- Built React frontend with modern UI
- Implemented watchlist management
- Added portfolio tracking
- Created interactive charts
- Made it mobile responsive

### ✅ Checkpoint #3 - Polish & Deployment Ready
- Added live market benchmarks
- Enhanced portfolio features
- Improved data fetching reliability
- Optimized performance
- Updated documentation
- Prepared for deployment

---

## 📚 Project Structure

```
Finvestor/
├── backend/              # Python FastAPI server
│   ├── app/
│   │   ├── api/         # Stock data endpoints
│   │   ├── services/    # Data fetching logic
│   │   └── models.py    # Database models
│   └── requirements.txt
├── frontend/             # React web application
│   ├── src/
│   │   ├── routes/      # Main pages (Portfolios, Watchlists, etc.)
│   │   ├── components/  # Reusable UI components
│   │   └── hooks/       # Data fetching and state management
│   └── package.json
└── docs/                 # Documentation
```

---

## 💼 About This Project

Finvestor was built as a senior capstone project for CS 498. The goal was to create a practical, real-world application that combines:
- **Full-stack development** (frontend + backend)
- **Database design** and management
- **API integration** with external data sources
- **Modern web technologies** and best practices
- **User experience** and interface design

This project demonstrates proficiency in building production-ready web applications that solve real problems for real users.

---

## 📅 What's Next?

Future enhancements planned for Finvestor:
- 🤖 **Portfolio Optimization** - AI-powered suggestions
- 📊 **Advanced Analytics** - Detailed performance metrics
- 🔔 **Price Alerts** - Get notified of significant moves
- 📰 **News Feed** - Latest stock news and events
- 🔄 **Auto-Rebalancing** - Maintain target allocations
- 📈 **Backtesting** - Test strategies with historical data

---

## 🎓 Educational Purpose

This is a student project created for educational purposes. While it uses real stock data, it is not intended as financial advice. Always consult with qualified financial professionals before making investment decisions.

---

**Built with ❤️ for smarter investing**

**Last Updated**: November 16, 2025  
**Version**: 3.0 (Checkpoint #3 Complete)
