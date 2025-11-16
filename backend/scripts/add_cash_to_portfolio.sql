-- Add cash field to portfolio table
-- Run this in pgAdmin or psql

ALTER TABLE portfolio 
ADD COLUMN IF NOT EXISTS cash NUMERIC(18, 2) DEFAULT 0.0 NOT NULL;

-- Update existing portfolios to have initial_value as cash if they have no holdings
UPDATE portfolio p
SET cash = COALESCE(p.initial_value, 0.0)
WHERE NOT EXISTS (
    SELECT 1 FROM portfolio_holding ph WHERE ph.portfolio_id = p.id
);

SELECT 'Cash column added successfully!' AS status;

