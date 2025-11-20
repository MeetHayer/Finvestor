# 📖 Finvestor User Guide

Complete guide to using all features of Finvestor.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Stock Analysis](#stock-analysis)
3. [Portfolio Management](#portfolio-management)
4. [Watchlists](#watchlists)
5. [Technical Indicators](#technical-indicators)
6. [Risk Metrics](#risk-metrics)
7. [Benchmark Comparisons](#benchmark-comparisons)

---

## Getting Started

### Home Page

When you first open Finvestor, you'll see:
- **Market Overview**: Current prices for major indices (SPY, QQQ, DIA)
- **Quick Tips**: Rotating tips about investing and using the platform
- **Navigation**: Sidebar with links to all features

### Search for Stocks

1. Click the **search bar** at the top
2. Type a stock symbol (e.g., "AAPL") or company name
3. Select from the dropdown results
4. View detailed analysis for that stock

---

## Stock Analysis

### Viewing Stock Data

**What you'll see:**
- **Current Price**: Latest trading price with daily change
- **Company Name**: Full company name below ticker symbol
- **Interactive Chart**: Candlestick or line chart showing price history
- **Volume**: Trading volume over time
- **Fundamentals**: P/E ratio, market cap, beta, 52-week high/low

### Chart Types

**Historical Charts (Daily Data):**
- Time ranges: 30 days, 90 days, 180 days, 1 year, 2 years, 5 years
- Chart types: Candlestick (default) or Line
- Zoom: Click and drag to zoom into specific date ranges
- Hover: See exact OHLCV data for any date

**Intraday Charts (1-Minute Data):**
- Shows last 7 days of 1-minute candles
- Auto-refreshes every 60 seconds
- Perfect for day trading or monitoring real-time movements
- Hover to see exact price at any minute

### Technical Indicators

**Available Indicators:**

1. **SMA (Simple Moving Average)**
   - Smooths price data to identify trends
   - Adjustable period (default: 20 days)
   - When price > SMA: Bullish signal
   - When price < SMA: Bearish signal

2. **EMA (Exponential Moving Average)**
   - Like SMA but gives more weight to recent prices
   - Adjustable period (default: 20 days)
   - Reacts faster to price changes than SMA

3. **RSI (Relative Strength Index)**
   - Measures momentum (0-100 scale)
   - RSI > 70: Overbought (potential sell signal)
   - RSI < 30: Oversold (potential buy signal)
   - Adjustable period (default: 14 days)

**How to Use:**
1. Toggle indicators on/off with checkboxes
2. Adjust periods using the number inputs
3. Indicators overlay on the main chart
4. RSI appears in a separate panel below

---

## Portfolio Management

### Creating a Portfolio

1. Go to **Portfolios** page
2. Click **"Create New Portfolio"**
3. Enter:
   - Portfolio name (e.g., "Retirement Fund")
   - Inception date (when you started investing)
   - Initial cash amount
4. Click **Create**

### Adding Holdings

1. Click **"Add Holding"** on your portfolio
2. Enter:
   - **Ticker symbol** (e.g., AAPL)
   - **Quantity** (number of shares)
   - **Purchase date** (when you bought it)
   - **Purchase price** (price per share)
3. Click **Add**

**The system will:**
- Fetch historical prices to calculate cost basis
- Update your cash balance
- Recalculate portfolio metrics
- Update the performance graph

### Selling Holdings

1. Click **"Sell"** next to any holding
2. Enter quantity to sell
3. See estimated proceeds based on current price
4. Click **Sell**

**The system will:**
- Add cash back to your portfolio
- Update holdings
- Recalculate metrics

### Portfolio Metrics

**Overview Metrics:**
- **Current Value**: Total portfolio worth today
- **Cash**: Available cash balance
- **Holdings Value**: Current value of all stocks
- **Return**: Percentage gain/loss since inception
- **Gain/Loss**: Dollar amount gained/lost

**Performance Graph:**
- Shows portfolio value over time
- Tracks every buy/sell transaction
- Updates daily with current prices
- Click **"View Full Analysis"** for detailed view

### Risk Metrics

Access detailed risk analysis by clicking **"View Full Analysis"**:

**Volatility (Annual):**
- Measures how much your portfolio value fluctuates
- Higher = More risky
- Calculated from daily returns over the entire history

**Sharpe Ratio:**
- Risk-adjusted return metric
- Compares your returns to risk-free rate (T-Bills)
- **> 1.0**: Good risk-adjusted returns
- **> 2.0**: Excellent
- **< 0**: Losing money or underperforming risk-free rate

**Max Drawdown:**
- Largest peak-to-trough decline
- Shows worst-case historical loss
- Lower = Better (more contained risk)
- Example: -15% means portfolio dropped 15% from its peak

**Value-at-Risk (VaR 95%):**
- Estimates potential loss in a bad day
- 95% confidence: You won't lose more than this 95% of the time
- Example: VaR = 2.5% means you could lose 2.5% of portfolio value on a bad day

**How to interpret:**
- Use Sharpe ratio to compare different portfolios
- Use Max Drawdown to understand worst-case scenarios
- Use VaR to set stop-loss limits

---

## Watchlists

### Creating a Watchlist

1. Go to **Watchlists** page
2. Click **"Create New Watchlist"**
3. Enter watchlist name (e.g., "Tech Stocks to Watch")
4. Click **Create**

### Adding Stocks

1. Click **"Add Stock"** on your watchlist
2. Search for ticker symbol
3. Click **Add**

### Watchlist Metrics

**For each stock, you'll see:**
- Current price
- Daily change ($ and %)
- Quick actions: View details or Remove

**Aggregate Metrics:**
- Average daily change across all stocks
- Best performer (highest % gain today)
- Worst performer (highest % loss today)

---

## Benchmark Comparisons

### What are Benchmarks?

Benchmarks let you compare your portfolio performance against major market indices to answer: **"Did I beat the market?"**

**Available Benchmarks:**
- **SPY**: S&P 500 (large-cap US stocks)
- **QQQ**: Nasdaq-100 (tech-heavy)
- **DIA**: Dow Jones Industrial Average (30 blue-chip stocks)

### How to Use

1. Go to **Portfolio Details** page (click "View Full Analysis")
2. Scroll to **"Compare with Benchmarks"** section
3. Click **"Overlay [SPY/QQQ/DIA]"** button
4. See benchmark returns overlaid on your portfolio graph

**What you'll see:**
- Your portfolio returns (blue line)
- Benchmark returns (colored line)
- Both start at 100% on your inception date
- Compare slopes to see who performed better

**Example:**
- Your portfolio: 100% → 125% (+25%)
- SPY benchmark: 100% → 115% (+15%)
- **You beat the market by 10%!** 🎉

### Interpreting Results

**Portfolio above benchmark:**
- You're outperforming the market
- Your stock picks are beating passive investing

**Portfolio below benchmark:**
- Market index would have been better
- Consider adjusting your strategy or just buying the index

**Portfolio tracks benchmark:**
- You're matching market returns
- Might be easier to just buy the index fund

---

## Tips & Best Practices

### Stock Analysis

✅ **Do:**
- Compare multiple timeframes (short-term vs long-term trends)
- Use indicators to confirm your analysis
- Check fundamentals (P/E ratio, market cap) before investing
- Look at volume to confirm price movements

❌ **Don't:**
- Rely on a single indicator
- Ignore fundamental analysis
- Trade based on emotions
- Forget to check the broader market context

### Portfolio Management

✅ **Do:**
- Diversify across different sectors
- Track your cost basis accurately
- Review risk metrics regularly
- Compare against benchmarks
- Set realistic return expectations

❌ **Don't:**
- Put all money in one stock
- Forget to account for transaction costs
- Panic sell during market dips
- Chase past performance

### Risk Management

✅ **Do:**
- Understand your risk tolerance
- Use Max Drawdown to set stop-losses
- Monitor Sharpe ratio for risk-adjusted returns
- Rebalance periodically

❌ **Don't:**
- Ignore volatility metrics
- Take on more risk than you can handle
- Compare returns without considering risk

---

## Keyboard Shortcuts

- **`/`**: Focus search bar
- **`Esc`**: Close modals
- **`←` / `→`**: Navigate tips carousel (Home page)

---

## Frequently Asked Questions

**Q: How often is data updated?**
A: Stock prices are cached for 5 minutes. Click "Refresh" for latest data. Intraday charts auto-refresh every 60 seconds.

**Q: Why is my Sharpe ratio N/A?**
A: You need to seed risk-free rate data. Run: `python3 backend/scripts/seed_risk_free_rate.py`

**Q: Can I import my existing portfolio?**
A: Not yet, but you can manually add all holdings with their purchase dates and prices.

**Q: Why doesn't my cost basis match the purchase price?**
A: The system fetches historical prices from the purchase date. If data is unavailable for that exact date, it uses the nearest available date.

**Q: What if a stock I own isn't in the database?**
A: The system automatically fetches data from Yahoo Finance when you search for any ticker. If it's a very obscure or delisted stock, it may not be available.

**Q: How accurate are the risk metrics?**
A: Risk metrics are calculated from historical data and are backward-looking. Past performance doesn't guarantee future results.

---

## Need More Help?

- **Technical Documentation**: See [FINVESTOR_DOCUMENTATION.md](./FINVESTOR_DOCUMENTATION.md)
- **Setup Issues**: See [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- **Recent Changes**: Check [CHANGELOG.md](./CHANGELOG.md)
- **API Keys**: See [API_KEYS.md](./API_KEYS.md)

---

**Happy Investing! 📈**

