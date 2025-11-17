# Import Local PostgreSQL Data to Railway

This is the **EASIEST** way to get your data into Railway - just copy it from your local database!

## Quick Steps (Essential Data Only):

### 1. Export Essential Tables from Local Database

```bash
cd backend/scripts
./export_essential_to_railway.sh
```

Or manually:
```bash
pg_dump "postgresql://finvestor:finvestor1234@localhost:5432/sampleStocksData" \
  --clean --if-exists --no-owner --no-acl \
  --format=custom \
  --table=ticker \
  --table=portfolio \
  --table=portfolio_holding \
  --table=portfolio_transaction \
  --table=portfolio_cash_ledger \
  --table=watchlist \
  --table=watchlist_tickers \
  --table=fundamentals_cache \
  --file=essential_data.dump
```

**Adjust the connection string** if your local database is different:
- Database name: `sampleStocksData`
- Username: `finvestor`
- Password: `finvestor1234`
- Host: `localhost`
- Port: `5432`

### 2. Get Railway DATABASE_URL

1. Go to Railway dashboard
2. Open your **PostgreSQL** service (not the backend)
3. Go to **Variables** tab
4. Copy the `DATABASE_URL` value
   - Looks like: `postgresql://postgres:password@host.railway.app:5432/railway`

### 3. Import to Railway

```bash
cd backend/scripts
./import_to_railway.sh "YOUR_RAILWAY_DATABASE_URL_HERE"
```

Or manually:
```bash
pg_restore -d "YOUR_RAILWAY_DATABASE_URL" \
  --clean --if-exists --no-owner --no-acl \
  --verbose \
  essential_data.dump
```

## That's It! 🎉

Your Railway database now has all your local data:
- ✅ All tables
- ✅ All stock data
- ✅ All portfolios
- ✅ All watchlists
- ✅ Everything!

## Optional: Full Database (Paid Plan Required)

If you have a paid Railway plan with enough disk space, you can still export/import everything:

```bash
./export_to_railway.sh     # Full dump (~1.3 GB)
./import_to_railway.sh "YOUR_RAILWAY_DATABASE_URL"
```

## Alternative: Using psql (if you prefer SQL)

If you want to use SQL instead of dump files:

```bash
# Export to SQL (full database)
pg_dump "postgresql://finvestor:finvestor1234@localhost:5432/sampleStocksData" \
  --clean --if-exists --no-owner --no-acl \
  > db_export.sql

# Import to Railway
psql "YOUR_RAILWAY_DATABASE_URL" < db_export.sql
```

## Troubleshooting

**"Connection refused" or "Name or service not known"**
- Make sure Railway PostgreSQL service is running
- Check that DATABASE_URL is correct
- Railway might need a few seconds to set up the connection

**"Permission denied"**
- Make sure scripts are executable: `chmod +x *.sh`

**"Database does not exist"**
- Railway creates the database automatically - just use the DATABASE_URL as-is

