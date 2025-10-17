# Finvestor Guardrails Document

**Created**: October 17, 2025  
**Last Updated**: October 17, 2025  
**Status**: BINDING - All developers must follow these rules

---

## Purpose

This document defines the **invariants** and **safety rules** that must be maintained throughout all refactoring and feature additions to Finvestor. Breaking these rules risks regressions and violates Checkpoint #2 acceptance criteria.

---

## Feature Invariants (MUST NOT CHANGE)

### 1. Watchlist CRUD Endpoints & Payloads
**Endpoints (must remain unchanged):**
- `GET /api/watchlists` - List all watchlists
- `POST /api/watchlists` - Create watchlist (body: `{name}`)
- `DELETE /api/watchlists/{id}` - Delete watchlist
- `GET /api/watchlists/{id}/tickers` - List tickers in watchlist
- `POST /api/watchlists/{id}/tickers` - Add ticker (body: `{symbol}`)
- `DELETE /api/watchlists/{id}/tickers/{symbol}` - Remove ticker

**Response Shape (must remain compatible):**
```json
{
  "id": "uuid",
  "name": "string",
  "created_at": "timestamp",
  "tickers": [{"symbol": "AAPL", "added_at": "timestamp"}]
}
```

**Rule:** Can ADD fields, cannot REMOVE or RENAME existing fields.

### 2. Portfolio Create/List Payloads
**Endpoints (must remain unchanged):**
- `GET /api/portfolios` - List all portfolios
- `POST /api/portfolios` - Create portfolio (body: `{name, inception_date, initial_value}`)
- `DELETE /api/portfolios/{id}` - Delete portfolio
- `GET /api/portfolios/{id}/holdings` - List holdings
- `POST /api/portfolios/{id}/holdings` - Add/update holding
- `DELETE /api/portfolios/{id}/holdings/{symbol}` - Remove holding

**Response Shape (must remain compatible):**
```json
{
  "id": "uuid",
  "name": "string",
  "inception_date": "date",
  "initial_value": "number",
  "created_at": "timestamp",
  "holdings": [{"symbol": "AAPL", "qty": 10, "avg_cost": 180.50, "as_of": "date"}]
}
```

**Rule:** `inception_date` must be stored and returned. Can ADD fields, cannot REMOVE or RENAME.

### 3. Ticker Page Candlestick Chart (OHLC Order)
**Invariants:**
- OHLC data must be in format: `[timestamp_ms, open, high, low, close, volume]`
- Chart must render candlestick on top pane, volume bar on bottom pane
- Time range selector (1W, 1M, 3M, 6M, 1Y) must properly filter data
- Chart must show latest data on the right (chronological order)

**Rule:** Do not change OHLC array structure. Chart bindings must stay intact.

### 4. Fundamentals Strip
**Required Metrics:**
- P/E Ratio (TTM)
- Market Cap
- Beta (if available)
- 52-Week High
- 52-Week Low

**Rule:** Must display "N/A" for missing values. Cannot remove any of these 5 metrics.

### 5. Benchmarks Card
**Invariants:**
- Must continue to render even if one or more symbols fail to fetch
- Partial success is acceptable (e.g., SPY succeeds, QQQ fails → show SPY)
- Must include error message for failed symbols

**Rule:** No endpoint should return 500 if a single benchmark fails. Return partial data with error fields.

---

## API Safety Rules

### Adding Fields (SAFE)
✅ **Allowed:**
```json
{
  "id": "uuid",
  "name": "My Portfolio",
  "inception_date": "2025-01-01",  // existing
  "last_updated": "2025-10-17"      // NEW - OK!
}
```

### Renaming/Removing Fields (FORBIDDEN)
❌ **Not Allowed:**
```json
{
  "id": "uuid",
  "portfolio_name": "My Portfolio",  // RENAMED from 'name' - BREAKS CLIENTS!
  // 'inception_date' removed - BREAKS CLIENTS!
}
```

### Breaking Change Mitigation
If a field must change:
1. Add new field with new name
2. Keep old field populated (adapter pattern)
3. Document deprecation in CHANGELOG.md
4. Plan removal for next major version

Example:
```json
{
  "inception_date": "2025-01-01",  // old field (deprecated but kept)
  "started_on": "2025-01-01"        // new field
}
```

---

## Database Safety Rules

### Additive Migrations Only (for CP2)
✅ **Allowed:**
- Add new columns (with DEFAULT values or nullable)
- Add new tables
- Add new indexes
- Add new functions/procedures

❌ **Not Allowed (for CP2):**
- Drop columns
- Rename columns (use aliases/views instead)
- Change column types (unless widening, e.g., VARCHAR(50) → VARCHAR(255))
- Drop tables still in use

### Migration Pattern
```sql
-- GOOD: Adding nullable column
ALTER TABLE portfolio ADD COLUMN description TEXT;

-- GOOD: Adding column with default
ALTER TABLE watchlist ADD COLUMN color VARCHAR(7) DEFAULT '#3B82F6';

-- BAD: Dropping column (breaks existing queries)
-- ALTER TABLE portfolio DROP COLUMN initial_value;  ❌

-- BAD: Renaming column (breaks existing queries)
-- ALTER TABLE portfolio RENAME COLUMN name TO portfolio_name;  ❌
```

---

## UI Safety Rules

### Default Behavior (No Flag)
All existing UI must render identically if `data-theme="elevate"` is **not** set on `<body>`.

**Rule:** New styling must be scoped under `[data-theme="elevate"]` selector:

```css
/* GOOD: Scoped to elevate theme */
[data-theme="elevate"] .card {
  border-radius: 1rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
}

/* BAD: Affects all themes */
.card {
  border-radius: 1rem;  /* Changes default look! */
}
```

### Testing Visual Changes
Before merging UI changes:
1. Test with `<body>` (no theme attribute) → must look identical to before
2. Test with `<body data-theme="elevate">` → can show new polish
3. Screenshot both for comparison

---

## Testing & Smoke Checklist

Before declaring any task "complete", run this checklist:

### Backend Smoke Tests
1. ✅ `GET /api/health` returns 200
2. ✅ `GET /api/benchmarks` returns data for SPY, QQQ, DIA (or errors)
3. ✅ `GET /api/data/AAPL` returns OHLC + fundamentals
4. ✅ `POST /api/watchlists` → `POST /api/watchlists/{id}/tickers` succeeds
5. ✅ `GET /api/watchlists` returns list with tickers
6. ✅ `POST /api/portfolios` with `inception_date` succeeds
7. ✅ `POST /api/portfolios/{id}/holdings` succeeds (with and without `avg_cost`)
8. ✅ `GET /api/portfolios` returns holdings with `inception_date`

### Frontend Smoke Tests
1. ✅ Navigate to Home → see benchmarks card (even if partial errors)
2. ✅ Click a ticker → chart renders with OHLC + volume
3. ✅ Change time range (1W, 1M, etc.) → chart updates correctly
4. ✅ Ticker detail → fundamentals show (P/E, Market Cap, Beta, 52W High/Low)
5. ✅ Watchlists page → create, add ticker, remove ticker, delete watchlist
6. ✅ Portfolios page → create with inception_date, add holding, view detail
7. ✅ Add holding without `avg_cost` → auto-fills from DB price
8. ✅ Mobile view → hamburger menu, responsive layout

### Regression Checks
- ✅ Existing watchlists still load
- ✅ Existing portfolios still load with all fields
- ✅ Chart interactions (zoom, pan, tooltip) still work
- ✅ No console errors in browser
- ✅ No 500 errors in backend logs

---

## File Change Protocol

### Before Editing Any File:
1. **Read this guardrails document**
2. **Check CHANGELOG.md** for recent changes to that file
3. **Grep for imports** of that file to understand dependencies
4. **Back up the current version** (or rely on git)

### After Editing:
1. **Test the affected feature** manually
2. **Run smoke checklist** (above)
3. **Update CHANGELOG.md** with:
   - Date
   - File(s) changed
   - Reason for change
   - User-visible impact
   - How to roll back (git commit hash)
4. **Update this guardrails doc** if new invariants emerge

---

## Deletion Protocol

### Before Deleting Any File:
1. **Run ripgrep** to find all imports/references:
   ```bash
   rg "filename" --type py --type js --type jsx
   ```
2. **If 0 results**, safe to delete
3. **If > 0 results**, must refactor those references first
4. **Document deletion in CHANGELOG.md** with:
   - Filename
   - Reason for deletion
   - Ripgrep evidence (paste output)
   - Alternative if needed

### Files That Must NOT Be Deleted (without approval):
- Any file under `backend/app/api/` (API routes)
- Any file under `backend/app/services/` (business logic)
- Any file under `backend/app/models.py` (database models)
- Any file under `frontend/src/routes/` (page components)
- Any file under `frontend/src/lib/` (utilities)

---

## Error Handling Standards

### API Endpoints Must:
1. **Return proper HTTP codes:**
   - 200 for success
   - 404 for not found (ticker, watchlist, portfolio)
   - 422 for validation errors (invalid date, missing required field)
   - 500 for unexpected server errors

2. **Return consistent error shape:**
   ```json
   {
     "detail": "Human-readable error message",
     "code": "TICKER_NOT_FOUND"  // optional machine-readable code
   }
   ```

3. **Log errors** to backend logs with:
   - Timestamp
   - Endpoint
   - Parameters
   - Stack trace (if exception)

### Frontend Must:
1. **Handle all error states** gracefully
2. **Show user-friendly messages** (not raw error text)
3. **Provide retry actions** where appropriate
4. **Never crash** - wrap risky operations in try/catch or error boundaries

---

## Performance Standards

### API Response Times (Target):
- `GET /api/data/{symbol}` (cached): < 100ms
- `GET /api/data/{symbol}` (live fetch): < 2s
- `GET /api/benchmarks` (live): < 3s (per symbol)
- All CRUD operations: < 200ms

### Database Queries:
- Add indexes for frequently queried columns:
  - `price_daily(symbol, date)`
  - `fundamentals_cache(symbol)`
  - `watchlist_tickers(watchlist_id, ticker_id)`
  - `portfolio_holding(portfolio_id, ticker_id)`

### Frontend Caching (React Query):
- `staleTime`: 5 minutes (data considered fresh)
- `cacheTime`: 30 minutes (data kept in cache)
- Invalidate on mutations (create, update, delete)

---

## Accessibility (A11y) Requirements

### Keyboard Navigation:
- All interactive elements (buttons, links, inputs) must be keyboard-accessible
- Focus states must be visible (ring-2 ring-primary/30)
- Modal traps must work (focus stays in modal until closed)

### Screen Readers:
- Use semantic HTML (`<button>`, `<nav>`, `<main>`, etc.)
- Add `aria-label` for icon-only buttons
- Add `aria-busy="true"` during loading states
- Add `aria-live="polite"` for dynamic content updates (toasts)

### Color Contrast:
- Text must meet WCAG AA standards (4.5:1 for normal text)
- Do not rely on color alone to convey information

---

## Code Style Conventions

### Python (Backend):
- Use `async/await` for all database operations
- Use Pydantic models for request/response validation
- Use type hints for all function parameters
- Use descriptive variable names (no `x`, `y`, `tmp`)
- Keep functions under 50 lines (split if longer)
- Log at appropriate levels:
  - `log.debug()` for verbose details
  - `log.info()` for important events
  - `log.warning()` for recoverable errors
  - `log.error()` / `log.exception()` for critical failures

### JavaScript/React (Frontend):
- Use functional components (no class components)
- Use hooks (useState, useEffect, useQuery, etc.)
- Extract reusable logic into custom hooks
- Keep components under 200 lines (split if longer)
- Use meaningful component names (PascalCase)
- Destructure props at the top of component
- Use `const` by default, `let` only when reassignment needed

### CSS (Tailwind):
- Prefer Tailwind utilities over custom CSS
- Group utilities logically: layout → spacing → colors → typography
- Use theme colors (primary, success, danger) over hardcoded hex
- Use responsive prefixes (sm:, md:, lg:) for breakpoints
- Extract repeated patterns into `@apply` classes (sparingly)

---

## Version Control Practices

### Commit Messages:
- Use conventional commit format:
  - `feat: Add benchmarks live data endpoint`
  - `fix: Correct OHLC array order in chart`
  - `refactor: Extract portfolio auto-pricing logic`
  - `docs: Update CHANGELOG with Task 2 changes`
  - `test: Add smoke tests for watchlist CRUD`

### Branching:
- `main` = production-ready code
- `feat/task-1-benchmarks` = feature branches
- Merge only when smoke tests pass

### Before Pushing:
1. Run smoke checklist
2. Update CHANGELOG.md
3. Update this guardrails doc if needed
4. Commit with meaningful message

---

## Mitigation Strategies

### If You Must Change an Existing Response Field:

**Option A: Adapter Pattern (Preferred)**
```python
# Old endpoint (keep working)
@router.get("/api/old")
async def old_endpoint():
    data = get_data()
    return {"old_field": data["new_field"]}  # Adapter

# New endpoint
@router.get("/api/new")
async def new_endpoint():
    data = get_data()
    return {"new_field": data["new_field"]}
```

**Option B: Dual Fields (Temporary)**
```python
return {
    "old_field": value,  # Deprecated but kept for compatibility
    "new_field": value   # Preferred field
}
```

### If You Must Change Database Schema:

**Option A: Add Column, Keep Old**
```sql
ALTER TABLE portfolio ADD COLUMN started_on DATE;
-- Populate from inception_date
UPDATE portfolio SET started_on = inception_date;
-- Keep inception_date for now (deprecate later)
```

**Option B: Create View**
```sql
CREATE VIEW portfolio_v2 AS
SELECT 
  id,
  name,
  inception_date AS started_on,  -- Rename via view
  initial_value
FROM portfolio;
```

---

## Approval Required For:

These changes require explicit approval before proceeding:
1. Removing any API endpoint
2. Changing any API response field name
3. Dropping any database column
4. Changing any existing React component's props interface (unless adding optional props)
5. Changing the OHLC array structure
6. Removing any of the 5 required fundamentals

If you need to do any of the above, document the reason in CHANGELOG.md and propose a mitigation strategy.

---

## Emergency Rollback

If a change causes regressions:
1. **Immediate**: `git revert <commit-hash>` and push
2. **Document**: Add incident report to CHANGELOG.md
3. **Diagnose**: Review guardrails violations
4. **Fix**: Re-implement with proper adapters/migration

---

## Success Metrics

A change is **acceptable** if:
1. ✅ All smoke tests pass
2. ✅ No existing API clients break
3. ✅ No visual regressions (unless behind theme flag)
4. ✅ Performance targets met
5. ✅ CHANGELOG.md updated
6. ✅ This guardrails doc updated (if new invariants)

---

## Contact & Questions

If unclear about any rule:
1. Read this document again
2. Check CHANGELOG.md for precedents
3. Test in a branch first
4. Document your decision in CHANGELOG.md

---

**Remember**: The goal is **zero regressions**. When in doubt, be conservative. Additive changes are safer than destructive ones.

---

**Document Version**: 1.0  
**Effective Date**: October 17, 2025  
**Review Date**: After each checkpoint completion

