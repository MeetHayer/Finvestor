# Finvestor Smoke Check Checklist

**Purpose**: Quick regression testing after any code changes  
**Duration**: ~10 minutes  
**Frequency**: Before every commit, after every feature

---

## Prerequisites

- Backend running on `localhost:8000`
- Frontend running on `localhost:5173`
- PostgreSQL with seeded data

---

## Backend Smoke Tests

### 1. Health Check
```bash
curl http://localhost:8000/api/health
# Expected: {"status": "ok", "db": true}
```
✅ Status: 200  
✅ DB connection: true

### 2. Benchmarks (Live Data)
```bash
curl http://localhost:8000/api/benchmarks
```
✅ Returns array of 3 items (SPY, QQQ, DIA)  
✅ Each has: `symbol`, `close`, `previous_close`, `change`, `change_pct`, `last_business_day`  
✅ Partial success OK (if one symbol has `error` field, others should still return data)

### 3. Search Ticker
```bash
curl "http://localhost:8000/api/search?q=AAP"
```
✅ Returns array with AAPL  
✅ Has: `symbol`, `name`, `source`

### 4. Get Market Data
```bash
curl "http://localhost:8000/api/data/AAPL"
```
✅ Returns: `symbol`, `latest` (with `close`, `prevClose`), `ohlc`, `fundamentals`  
✅ OHLC array format: `[timestamp_ms, open, high, low, close, volume]`  
✅ Fundamentals has: `trailingPE`, `marketCap`, `fiftyTwoWeekHigh`, `fiftyTwoWeekLow`

### 5. Watchlist CRUD
```bash
# Create
curl -X POST http://localhost:8000/api/watchlists \
  -H "Content-Type: application/json" \
  -d '{"name": "Smoke Test WL"}'
# Save the returned ID

# Add ticker
curl -X POST "http://localhost:8000/api/watchlists/{ID}/tickers" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'

# List
curl http://localhost:8000/api/watchlists
# Verify "Smoke Test WL" appears with AAPL in tickers array

# Delete
curl -X DELETE "http://localhost:8000/api/watchlists/{ID}"
```
✅ Create returns new watchlist with ID  
✅ Add ticker succeeds  
✅ List shows watchlist with ticker  
✅ Delete succeeds

### 6. Portfolio CRUD with Auto-Pricing
```bash
# Create portfolio
curl -X POST http://localhost:8000/api/portfolios \
  -H "Content-Type: application/json" \
  -d '{"name": "Smoke Test Portfolio", "inception_date": "2025-01-01", "initial_value": 10000}'
# Save the returned ID

# Add holding WITH avg_cost (manual pricing)
curl -X POST "http://localhost:8000/api/portfolios/{ID}/holdings" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "qty": 10, "avg_cost": 180.50}'

# Add holding WITHOUT avg_cost (auto-pricing)
curl -X POST "http://localhost:8000/api/portfolios/{ID}/holdings" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "MSFT", "qty": 5, "as_of": "2025-10-01"}'

# List portfolios
curl http://localhost:8000/api/portfolios
# Verify portfolio has 2 holdings, MSFT has auto_priced: true

# Delete
curl -X DELETE "http://localhost:8000/api/portfolios/{ID}"
```
✅ Create returns portfolio with `inception_date`  
✅ Add holding with manual cost succeeds  
✅ Add holding without cost auto-fills from DB  
✅ Auto-pricing returns 422 if no price data available (test with old date like "2020-01-01")  
✅ Delete succeeds

---

## Frontend Smoke Tests

### 1. Home Page - Benchmarks
1. Navigate to `http://localhost:5173`
2. Check "Market Overview" or benchmarks card
3. ✅ Shows SPY, QQQ, DIA with prices and % change
4. ✅ Shows "As of {last_business_day}"
5. ✅ Partial errors OK (e.g., "SPY: Error fetching data" but others load)

### 2. Ticker Detail Page
1. Click on any ticker or navigate to `/ticker/AAPL`
2. ✅ Chart renders with candlestick (top) and volume bars (bottom)
3. ✅ Time range buttons (1W, 1M, 3M, 6M, 1Y) work
4. ✅ Chart updates when clicking different time ranges
5. ✅ Fundamentals strip shows: P/E, Market Cap, Beta, 52W High, 52W Low
6. ✅ "N/A" displayed for any missing fundamentals

### 3. Watchlists Page
1. Navigate to `/watchlists`
2. ✅ Click "Create Watchlist" → modal opens
3. ✅ Enter name → submit → watchlist appears
4. ✅ Click "Add Ticker" → search works (autocomplete)
5. ✅ Add AAPL → appears in watchlist card
6. ✅ Click X on ticker chip → ticker removed
7. ✅ Click "Delete Watchlist" → watchlist removed
8. ✅ No console errors

### 4. Portfolios Page
1. Navigate to `/portfolios`
2. ✅ Click "Create Portfolio" → modal opens
3. ✅ Enter name, inception_date, initial_value → submit → portfolio appears
4. ✅ Click "Add Holding" → modal opens
5. ✅ Enter symbol, shares, **leave avg_cost blank** → submit → holding added
6. ✅ Verify "auto_priced" indicator or auto-filled cost value
7. ✅ Add another holding with manual avg_cost → works
8. ✅ Click X on holding → removed
9. ✅ Click "Delete Portfolio" → portfolio removed

### 5. Portfolio Detail Page
1. From Portfolios page, click "View Details" on a portfolio
2. ✅ Shows inception date card
3. ✅ Shows initial value card
4. ✅ Shows holdings value card (calculated)
5. ✅ Holdings table displays: Symbol, Shares, Avg Cost, Total Value, Added On
6. ✅ Symbol links to ticker detail page
7. ✅ Total portfolio value shown at bottom
8. ✅ Empty state shown if no holdings
9. ✅ "Back to Portfolios" link works

### 6. Mobile Responsive
1. Resize browser to < 768px or use mobile device
2. ✅ Hamburger menu appears
3. ✅ Sidebar slides in/out on click
4. ✅ Charts stack vertically
5. ✅ Tables scroll horizontally
6. ✅ Cards stack in single column

### 7. Loading States & Errors
1. Navigate to any page
2. ✅ Skeleton loaders appear during fetch
3. ✅ No "undefined" or "null" displayed in UI
4. ✅ Error states have friendly messages
5. ✅ Error states have retry/back buttons

---

## Regression Checks

### Must NOT Break:
- ✅ Existing watchlists still load
- ✅ Existing portfolios still load with all fields (`inception_date` intact)
- ✅ Chart OHLC order correct (Open, High, Low, Close)
- ✅ Chart volume pane renders separately below candlesticks
- ✅ Fundamentals always show 5 metrics (P/E, Market Cap, Beta, 52W High, 52W Low)
- ✅ API responses have same fields as before (additive changes only)
- ✅ No 500 errors in backend logs
- ✅ No console errors in browser
- ✅ Toast notifications appear on actions (create, delete, add, remove)

---

## Performance Checks

### Target Response Times:
- ✅ `GET /api/data/{symbol}` (cached): < 100ms
- ✅ `GET /api/data/{symbol}` (live): < 2s
- ✅ `GET /api/benchmarks` (live): < 3s per symbol
- ✅ All CRUD operations: < 200ms
- ✅ Chart renders: < 500ms
- ✅ Page transitions: < 300ms (Framer Motion animations)

### Cache Verification:
1. Open Network tab in browser DevTools
2. Navigate to ticker detail page
3. ✅ First load: see API call to `/api/data/AAPL`
4. Navigate away and back within 5 minutes
5. ✅ Second load: no API call (React Query cache hit)

---

## Accessibility (A11y) Quick Checks

- ✅ Tab through interactive elements (buttons, links, inputs)
- ✅ Focus indicators visible (ring around focused elements)
- ✅ Modal traps focus (can't tab outside modal)
- ✅ Color contrast sufficient (text readable)
- ✅ No "click div" elements (all buttons are `<button>`, links are `<a>`)

---

## Browser Console Checks

### No Errors:
- ✅ Zero JavaScript errors
- ✅ Zero React warnings about keys/props
- ✅ Zero CORS errors
- ✅ Zero 404s for assets

### Expected Warnings (OK to ignore):
- React Query devtools warnings (development only)
- Vite HMR messages (development only)

---

## Backend Logs Check

```bash
tail -f backend/logs/app.log
```

### Expected:
- ✅ INFO logs for successful requests
- ✅ WARNING logs for expected failures (rate limits, missing data)
- ✅ No ERROR or EXCEPTION logs (unless expected)

### Red Flags:
- ❌ Repeated EXCEPTION stack traces
- ❌ 500 Internal Server Error
- ❌ Database connection errors

---

## Sign-Off Checklist

Before committing:
- [ ] All backend smoke tests pass
- [ ] All frontend smoke tests pass
- [ ] No regressions found
- [ ] Performance targets met
- [ ] No console errors
- [ ] No backend exceptions
- [ ] CHANGELOG.md updated
- [ ] Guardrails doc reviewed

**Smoke Test Passed**: ✅ / ❌  
**Tester**: ___________  
**Date**: ___________  
**Notes**: ___________

---

## Troubleshooting

### Issue: Benchmarks fail with "No data available"
**Solution**: Check yahoo_fin package installed (`pip list | grep yahoo-fin`)

### Issue: Auto-pricing returns 422
**Solution**: Verify price_daily has data for that ticker/date. Try a recent date like today or yesterday.

### Issue: Chart not rendering
**Solution**: Check OHLC array format. Must be `[timestamp_ms, open, high, low, close, volume]`

### Issue: Hooks import error
**Solution**: Verify `frontend/src/hooks/useWatchlists.js` and `usePortfolios.js` exist

### Issue: Portfolio detail page 404
**Solution**: Check route in App.jsx includes `/portfolio/:id` (with `:id` param)

---

**Last Updated**: October 17, 2025  
**Version**: 1.0

