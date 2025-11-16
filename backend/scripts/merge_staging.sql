-- Merge staging_prices data into main ticker and price_daily tables
-- Then drop the staging table

-- Step 1: Insert/update ticker records from staging (symbol only, name will be updated later)
INSERT INTO ticker (symbol, name, exchange)
SELECT DISTINCT 
    symbol,
    symbol as name,  -- Use symbol as name initially
    'UNKNOWN' as exchange
FROM staging_prices
ON CONFLICT (symbol) DO NOTHING;

-- Step 2: Insert price_daily records (matching by ticker_id from JOIN)
INSERT INTO price_daily (ticker_id, date, open, high, low, close, volume)
SELECT 
    t.id as ticker_id,
    s.date,
    s.open::NUMERIC(18,6) as open,
    s.high::NUMERIC(18,6) as high,
    s.low::NUMERIC(18,6) as low,
    s.close::NUMERIC(18,6) as close,
    s.volume::BIGINT as volume
FROM staging_prices s
JOIN ticker t ON t.symbol = s.symbol
WHERE s.close IS NOT NULL  -- Only rows with valid close price
ON CONFLICT (ticker_id, date) DO NOTHING;

-- Step 3: Show summary before dropping staging
SELECT 
    'Summary before cleanup:' as info,
    (SELECT COUNT(DISTINCT symbol) FROM staging_prices) as staging_symbols,
    (SELECT COUNT(*) FROM staging_prices) as staging_rows,
    (SELECT COUNT(DISTINCT symbol) FROM ticker) as ticker_count,
    (SELECT COUNT(*) FROM price_daily) as price_daily_count;

-- Step 4: Drop staging table
DROP TABLE IF EXISTS staging_prices;

-- Final summary
SELECT 
    'Final counts:' as info,
    (SELECT COUNT(DISTINCT symbol) FROM ticker) as total_symbols,
    (SELECT COUNT(*) FROM price_daily) as total_price_records,
    (SELECT AVG(cnt)::INT FROM (
        SELECT COUNT(*) as cnt FROM price_daily GROUP BY ticker_id
    ) sub) as avg_records_per_symbol;
