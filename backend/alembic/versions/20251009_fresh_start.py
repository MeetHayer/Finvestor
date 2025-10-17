from alembic import op
import sqlalchemy as sa

revision = 'fresh_start_20251009'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    CREATE TABLE IF NOT EXISTS watchlist (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      name TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS watchlist_tickers (
      watchlist_id UUID NOT NULL REFERENCES watchlist(id) ON DELETE CASCADE,
      symbol TEXT NOT NULL,
      added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (watchlist_id, symbol)
    );

    CREATE TABLE IF NOT EXISTS portfolio (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      name TEXT NOT NULL,
      inception_date DATE NOT NULL,
      initial_value NUMERIC(18,2) NOT NULL DEFAULT 0,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS portfolio_holding (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      portfolio_id UUID NOT NULL REFERENCES portfolio(id) ON DELETE CASCADE,
      symbol TEXT NOT NULL,
      qty NUMERIC(24,6) NOT NULL,
      avg_cost NUMERIC(18,4) NOT NULL,
      as_of DATE NOT NULL DEFAULT CURRENT_DATE,
      CONSTRAINT uq_portfolio_symbol UNIQUE (portfolio_id, symbol)
    );
    """)

def downgrade():
    op.execute("""
    DROP TABLE IF EXISTS portfolio_holding;
    DROP TABLE IF EXISTS portfolio;
    DROP TABLE IF EXISTS watchlist_tickers;
    DROP TABLE IF EXISTS watchlist;
    """)


