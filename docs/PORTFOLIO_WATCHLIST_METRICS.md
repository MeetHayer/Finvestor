# 📊 Portfolio & Watchlist Metrics - Complete Guide

## 🎯 Overview

I've added comprehensive calculated metrics for both **Portfolios** and **Watchlists** that provide real-time insights into your investments.

---

## 📈 Portfolio Metrics

### **New API Endpoint:**
```
GET /api/portfolios/{portfolio_id}/metrics
```

### **Calculated Fields:**

#### **Portfolio-Level Metrics:**
| Field | Description | Example |
|-------|-------------|---------|
| `current_value` | Total current value of all positions | $52,450.00 |
| `total_cost` | Total cost basis of all positions | $50,000.00 |
| `total_return_dollar` | Total return in dollars | $2,450.00 |
| `total_return_pct` | Total return as percentage | 4.9% |
| `portfolio_return_dollar` | Return since inception vs initial value | $2,450.00 |
| `portfolio_return_pct` | Return % since inception | 4.9% |
| `average_beta` | Weighted average beta of all positions | 1.15 |
| `inception_days` | Days since portfolio creation | 365 |
| `num_positions` | Number of holdings | 5 |

#### **Position-Level Metrics (for each holding):**
| Field | Description | Example |
|-------|-------------|---------|
| `symbol` | Stock ticker | AAPL |
| `name` | Company name | Apple Inc. |
| `shares` | Number of shares owned | 100 |
| `cost_basis` | Price paid per share | $150.00 |
| `current_price` | Current price per share | $175.00 |
| `position_value` | Current value of position | $17,500.00 |
| `position_cost` | Total cost of position | $15,000.00 |
| `return_dollar` | Position return in dollars | $2,500.00 |
| `return_pct` | Position return as percentage | 16.67% |
| `holding_period_days` | Days held | 180 |
| `beta` | Stock's beta coefficient | 1.2 |
| `weight` | Position weight in portfolio | 33.4% |

### **Example Response:**
```json
{
  "portfolio_id": "a1b2c3d4-...",
  "name": "Growth Portfolio",
  "inception_date": "2024-01-01",
  "inception_days": 283,
  "initial_value": 50000.00,
  "current_value": 52450.00,
  "total_cost": 50000.00,
  "total_return_dollar": 2450.00,
  "total_return_pct": 4.9,
  "portfolio_return_dollar": 2450.00,
  "portfolio_return_pct": 4.9,
  "average_beta": 1.15,
  "num_positions": 3,
  "positions": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "shares": 100,
      "cost_basis": 150.00,
      "current_price": 175.00,
      "position_value": 17500.00,
      "position_cost": 15000.00,
      "return_dollar": 2500.00,
      "return_pct": 16.67,
      "holding_period_days": 180,
      "beta": 1.2,
      "weight": 33.4
    },
    {
      "symbol": "MSFT",
      "name": "Microsoft Corporation",
      "shares": 50,
      "cost_basis": 300.00,
      "current_price": 350.00,
      "position_value": 17500.00,
      "position_cost": 15000.00,
      "return_dollar": 2500.00,
      "return_pct": 16.67,
      "holding_period_days": 150,
      "beta": 1.1,
      "weight": 33.4
    }
  ]
}
```

---

## 📋 Watchlist Metrics

### **New API Endpoint:**
```
GET /api/watchlists/{watchlist_id}/metrics
```

### **Calculated Fields (for each ticker):**
| Field | Description | Example |
|-------|-------------|---------|
| `symbol` | Stock ticker | AAPL |
| `name` | Company name | Apple Inc. |
| `current_price` | Latest closing price | $175.00 |
| `daily_change_dollar` | Change from yesterday ($) | +$2.50 |
| `daily_change_pct` | Change from yesterday (%) | +1.45% |
| `weekly_change_dollar` | Change from 7 days ago ($) | +$5.75 |
| `weekly_change_pct` | Change from 7 days ago (%) | +3.40% |
| `market_cap` | Market capitalization | 2,750,000,000,000 |
| `pe_ratio` | Price-to-earnings ratio | 28.5 |
| `beta` | Beta coefficient | 1.2 |
| `week_52_high` | 52-week high price | $198.23 |
| `week_52_low` | 52-week low price | $142.56 |

### **Example Response:**
```json
{
  "watchlist_id": "x1y2z3a4-...",
  "name": "Tech Favorites",
  "description": "My favorite tech stocks",
  "num_tickers": 3,
  "tickers": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "current_price": 175.00,
      "daily_change_dollar": 2.50,
      "daily_change_pct": 1.45,
      "weekly_change_dollar": 5.75,
      "weekly_change_pct": 3.40,
      "market_cap": 2750000000000,
      "pe_ratio": 28.5,
      "beta": 1.2,
      "week_52_high": 198.23,
      "week_52_low": 142.56
    },
    {
      "symbol": "MSFT",
      "name": "Microsoft Corporation",
      "current_price": 350.00,
      "daily_change_dollar": -1.25,
      "daily_change_pct": -0.36,
      "weekly_change_dollar": 8.50,
      "weekly_change_pct": 2.49,
      "market_cap": 2600000000000,
      "pe_ratio": 32.1,
      "beta": 1.1,
      "week_52_high": 375.50,
      "week_52_low": 285.00
    }
  ]
}
```

---

## 🔧 How It Works

### **Portfolio Metrics Calculation:**
1. **Fetches all holdings** for the portfolio
2. **Gets current prices** from `price_daily` table (latest entry)
3. **Calculates position metrics:**
   - Position value = current_price × shares
   - Position cost = cost_basis × shares
   - Return = position_value - position_cost
   - Holding period = today - added_at date
4. **Gets beta** from `fundamentals_cache` table
5. **Calculates portfolio-level metrics:**
   - Total value = sum of all position values
   - Total cost = sum of all position costs
   - Average beta = weighted average by position value
   - Portfolio return = current_value - initial_value

### **Watchlist Metrics Calculation:**
1. **Fetches all tickers** in the watchlist
2. **Gets latest price** from `price_daily` table
3. **Gets price from 1 day ago** for daily change
4. **Gets price from 7 days ago** for weekly change
5. **Calculates changes:**
   - Daily change = current_price - yesterday_price
   - Weekly change = current_price - week_ago_price
6. **Gets fundamentals** from `fundamentals_cache` table

---

## 🎨 Frontend Integration

### **Portfolio Page Enhancement:**
```javascript
// Fetch portfolio metrics
const { data: metrics } = useQuery({
  queryKey: ['portfolioMetrics', portfolioId],
  queryFn: () => getJSON(`/portfolios/${portfolioId}/metrics`)
});

// Display metrics
<div>
  <h2>Portfolio Value: ${metrics.current_value.toLocaleString()}</h2>
  <p>Total Return: ${metrics.total_return_dollar} ({metrics.total_return_pct}%)</p>
  <p>Average Beta: {metrics.average_beta}</p>
  
  {metrics.positions.map(pos => (
    <div key={pos.symbol}>
      <h3>{pos.symbol} - {pos.name}</h3>
      <p>Shares: {pos.shares}</p>
      <p>Value: ${pos.position_value}</p>
      <p>Return: ${pos.return_dollar} ({pos.return_pct}%)</p>
      <p>Held for: {pos.holding_period_days} days</p>
    </div>
  ))}
</div>
```

### **Watchlist Page Enhancement:**
```javascript
// Fetch watchlist metrics
const { data: metrics } = useQuery({
  queryKey: ['watchlistMetrics', watchlistId],
  queryFn: () => getJSON(`/watchlists/${watchlistId}/metrics`)
});

// Display metrics
<div>
  {metrics.tickers.map(ticker => (
    <div key={ticker.symbol}>
      <h3>{ticker.symbol} - {ticker.name}</h3>
      <p>Price: ${ticker.current_price}</p>
      <p className={ticker.daily_change_pct >= 0 ? 'green' : 'red'}>
        Daily: {ticker.daily_change_dollar} ({ticker.daily_change_pct}%)
      </p>
      <p className={ticker.weekly_change_pct >= 0 ? 'green' : 'red'}>
        Weekly: {ticker.weekly_change_dollar} ({ticker.weekly_change_pct}%)
      </p>
      <p>P/E: {ticker.pe_ratio} | Beta: {ticker.beta}</p>
      <p>52W: ${ticker.week_52_low} - ${ticker.week_52_high}</p>
    </div>
  ))}
</div>
```

---

## 🚀 Usage Examples

### **Test Portfolio Metrics:**
```bash
# Get metrics for a portfolio
curl http://localhost:8000/api/portfolios/{portfolio_id}/metrics
```

### **Test Watchlist Metrics:**
```bash
# Get metrics for a watchlist
curl http://localhost:8000/api/watchlists/{watchlist_id}/metrics
```

---

## 📊 Key Features

### **Portfolio:**
✅ **Real-time valuation** - Current value of all holdings  
✅ **Return tracking** - Dollar and percentage returns  
✅ **Holding period analysis** - Days held for each position  
✅ **Risk metrics** - Weighted average beta  
✅ **Position weighting** - Percentage of portfolio per stock  
✅ **Cost basis tracking** - Original purchase prices  

### **Watchlist:**
✅ **Live prices** - Current market prices  
✅ **Daily changes** - Today's performance  
✅ **Weekly changes** - 7-day performance  
✅ **Fundamentals** - P/E, Market Cap, Beta  
✅ **52-week range** - High and low prices  
✅ **Quick comparison** - See all stocks at a glance  

---

## 🎯 Next Steps

1. **Frontend Integration**: Create beautiful UI components to display these metrics
2. **Real-time Updates**: Add WebSocket support for live price updates
3. **Charts**: Add performance charts using the calculated metrics
4. **Alerts**: Set up price alerts based on daily/weekly changes
5. **Export**: Allow users to export metrics to CSV/PDF

---

## 📝 Notes

- All calculations are done **server-side** for consistency
- Metrics are **calculated on-demand** (not stored in DB)
- **Caching** is handled by React Query on frontend
- **Price data** must exist in `price_daily` table
- **Fundamentals** must exist in `fundamentals_cache` table
- If data is missing, fields will be `null` or `0`

---

**The metrics system is now ready for production use!** 🎉


