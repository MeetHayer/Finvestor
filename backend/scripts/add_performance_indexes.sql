-- Performance Indexes for Finvestor
-- Run this SQL script in pgAdmin or psql to add indexes
-- These indexes optimize frequently queried columns
-- Safe to run multiple times (IF NOT EXISTS)

-- Index for price_daily lookups by ticker and date
-- Used by: chart rendering, auto-pricing, portfolio valuations
CREATE INDEX IF NOT EXISTS idx_price_daily_ticker_date 
ON price_daily(ticker_id, date DESC);

-- Index for fundamentals cache lookups
-- Used by: ticker detail page fundamentals display
CREATE INDEX IF NOT EXISTS idx_fundamentals_ticker 
ON fundamentals_cache(ticker_id);

-- Index for watchlist_tickers association lookups
-- Used by: watchlist detail, add/remove ticker operations
CREATE INDEX IF NOT EXISTS idx_watchlist_tickers_watchlist 
ON watchlist_tickers(watchlist_id, ticker_id);

-- Index for portfolio_holding association lookups
-- Used by: portfolio detail, add/remove holding operations
CREATE INDEX IF NOT EXISTS idx_portfolio_holding_portfolio 
ON portfolio_holding(portfolio_id, ticker_id);

-- Index for ticker symbol lookups (commonly searched)
-- Used by: search, symbol resolution
CREATE INDEX IF NOT EXISTS idx_ticker_symbol 
ON ticker(symbol);

-- Composite index for portfolio holdings with trade date
-- Used by: portfolio history, performance calculations
CREATE INDEX IF NOT EXISTS idx_portfolio_holding_date 
ON portfolio_holding(portfolio_id, added_at DESC);

-- Print success message
SELECT 'Performance indexes created successfully!' AS status;

