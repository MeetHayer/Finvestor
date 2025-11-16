"""
Seed database from Kaggle dataset: "Huge Stock Market Dataset"
Dataset: borismarjanovic/price-volume-data-for-all-us-stocks-etfs
Loads *.us.txt files and populates staging_prices table
"""
import os
import sys
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import make_url
from dotenv import load_dotenv
import logging
import zipfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def _with_driver(url: str, driver: str = "psycopg") -> str:
    parsed = make_url(url)
    return str(parsed.set(drivername=f"postgresql+{driver}"))


def get_database_url(driver: str = "psycopg"):
    """Get DATABASE_URL/Postgres DSN with explicit driver."""
    db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
    if not db_url:
        raise RuntimeError("DATABASE_URL or POSTGRES_DSN not set in .env")
    return _with_driver(db_url, driver)


def create_staging_table(engine):
    """Create staging_prices table if it doesn't exist"""
    with engine.connect() as conn:
        # Check if table exists
        inspector = inspect(engine)
        if 'staging_prices' in inspector.get_table_names():
            logger.info("staging_prices table already exists (truncating for fresh load)...")
            conn.execute(text("TRUNCATE TABLE staging_prices"))
            conn.commit()
            return
        
        # Create table
        logger.info("Creating staging_prices table...")
        conn.execute(text("""
            CREATE TABLE staging_prices (
                date DATE NOT NULL,
                open FLOAT,
                high FLOAT,
                low FLOAT,
                close FLOAT,
                volume BIGINT,
                open_interest BIGINT,
                symbol TEXT NOT NULL,
                PRIMARY KEY (date, symbol)
            )
        """))
        conn.commit()
        logger.info("✓ staging_prices table created")


def find_dataset_folder(dataset_path: Path):
    """Find the folder containing .us.txt files"""
    # kagglehub downloads to a path, might be zipped or in subfolders
    if dataset_path.is_file() and dataset_path.suffix == '.zip':
        # Extract zip if needed
        extract_to = dataset_path.parent / dataset_path.stem
        if not extract_to.exists():
            logger.info(f"Extracting {dataset_path.name}...")
            with zipfile.ZipFile(dataset_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        dataset_path = extract_to
    
    # Look for .us.txt files in current dir and subdirs
    search_paths = [
        dataset_path,
        dataset_path / "Data" / "Stocks",
        dataset_path / "stocks",
        dataset_path / "data",
    ]
    
    for search_path in search_paths:
        if search_path.exists():
            us_files = list(search_path.glob("**/*.us.txt"))
            if us_files:
                logger.info(f"Found {len(us_files)} .us.txt files in {search_path}")
                return search_path, us_files
    
    # Last resort: search all subdirectories
    logger.info("Searching all subdirectories for .us.txt files...")
    all_us_files = list(dataset_path.glob("**/*.us.txt"))
    if all_us_files:
        logger.info(f"Found {len(all_us_files)} .us.txt files in subdirectories")
        return dataset_path, all_us_files
    
    # Error: show directory structure for debugging
    logger.error(f"❌ No .us.txt files found in {dataset_path}")
    logger.error("Directory structure:")
    for item in sorted(dataset_path.rglob("*"))[:20]:  # Show first 20 items
        if item.is_file():
            logger.error(f"  FILE: {item.relative_to(dataset_path)}")
        elif item.is_dir():
            logger.error(f"  DIR:  {item.relative_to(dataset_path)}/")
    
    return None, []


def process_file(file_path: Path, symbol: str, engine):
    """Process a single .us.txt file and load into staging_prices"""
    try:
        # Read the file (CSV format)
        df = pd.read_csv(file_path, sep=',', header=0)
        
        # Normalize column names
        df.columns = [col.strip() for col in df.columns]
        
        # Map column names
        column_mapping = {
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'OpenInt': 'open_interest'
        }
        
        for old_col in list(df.columns):
            if old_col in column_mapping:
                df = df.rename(columns={old_col: column_mapping[old_col]})
        
        # Check required columns
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"  ⚠️  {file_path.name}: Missing columns {missing_cols}, skipping")
            return 0
        
        # Add open_interest if missing
        if 'open_interest' not in df.columns:
            df['open_interest'] = None
        
        # Add symbol column
        df['symbol'] = symbol
        
        # Convert date column
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
        df = df.dropna(subset=['date'])
        
        # Convert to numeric
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'open_interest']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Clean: remove rows with missing essential data
        df = df.dropna(subset=['close'])
        
        if len(df) == 0:
            logger.warning(f"  ⚠️  {file_path.name}: No valid data rows after cleaning")
            return 0
        
        # Insert into staging table
        with engine.connect() as conn:
            df_to_insert = df[['date', 'open', 'high', 'low', 'close', 'volume', 'open_interest', 'symbol']].copy()
            
            df_to_insert.to_sql(
                'staging_prices',
                conn,
                if_exists='append',
                index=False,
                method='multi'
            )
            conn.commit()
        
        logger.info(f"  ✓ Loaded: {symbol} ({len(df_to_insert)} rows)")
        return len(df_to_insert)
        
    except Exception as e:
        logger.error(f"  ❌ Error processing {file_path.name}: {str(e)[:100]}")
        import traceback
        logger.debug(traceback.format_exc())
        return 0


def main():
    """Main function to seed from Kaggle"""
    try:
        import kagglehub
    except ImportError:
        logger.error("❌ kagglehub not installed. Run: pip install kagglehub")
        return
    
    logger.info("=" * 70)
    logger.info("🚀 Starting Kaggle Dataset Seeding")
    logger.info("=" * 70)
    
    # Get database connection
    db_url = get_database_url()
    db_name = db_url.split('@')[1].split('/')[-1] if '@' in db_url else 'local'
    logger.info(f"Database: {db_name}")
    
    # Create engine (using psycopg for sync operations)
    engine = create_engine(db_url, echo=False)
    
    # Create staging table
    create_staging_table(engine)
    
    # Download dataset
    logger.info("Downloading dataset from Kaggle...")
    try:
        dataset_path = kagglehub.dataset_download("borismarjanovic/price-volume-data-for-all-us-stocks-etfs")
        logger.info(f"✓ Dataset downloaded to: {dataset_path}")
    except Exception as e:
        logger.error(f"❌ Failed to download dataset: {e}")
        logger.error("Make sure you have:")
        logger.error("  1. Kaggle account (free)")
        logger.error("  2. kaggle.json API credentials in ~/.kaggle/kaggle.json")
        logger.error("  3. Run: chmod 600 ~/.kaggle/kaggle.json")
        return
    
    # Find dataset folder and .us.txt files
    dataset_path = Path(dataset_path)
    folder_path, us_files = find_dataset_folder(dataset_path)
    
    if not us_files:
        logger.error("❌ No .us.txt files found. Cannot proceed.")
        return
    
    logger.info(f"Found {len(us_files)} .us.txt files total")
    
    # Process all files (remove test limit)
    files_to_process = us_files
    logger.info(f"Processing {len(files_to_process)} files...")
    logger.info("")
    
    total_rows = 0
    success_count = 0
    
    for txt_file in files_to_process:
        # Extract symbol from filename (e.g., "AAPL.us.txt" -> "AAPL")
        symbol = txt_file.stem.replace('.us', '').upper()
        
        rows_inserted = process_file(txt_file, symbol, engine)
        if rows_inserted > 0:
            success_count += 1
            total_rows += rows_inserted
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"✅ Seeding complete!")
    logger.info(f"   Successfully loaded: {success_count}/{len(files_to_process)} symbols")
    logger.info(f"   Total rows inserted: {total_rows:,}")
    logger.info("=" * 70)
    
    if success_count > 0:
        logger.info("")
        logger.info("Next step: Run merge_staging.sql to merge into main tables:")
        logger.info("  psql -U finvestor -h localhost -d sampleStocksData -f scripts/merge_staging.sql")


if __name__ == "__main__":
    main()

# ==== FLEXIBLE CSV IMPORT FOR PRICES & NAMES ====
import csv
from datetime import datetime as _dt, date as _date
from sqlalchemy import text

def _norm_header(h: str) -> str:
    return (h or "").strip().lower().replace(" ", "").replace("_","")

def _parse_date_flex(s: str) -> _date:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return _dt.strptime(s, fmt).date()
        except ValueError:
            continue
    return _dt.fromisoformat(s).date()

def upsert_names_csv(engine, path: str) -> int:
    """
    Flexible columns: Symbol/Ticker, Name/Company
    UPSERTS into ticker(symbol,name). Creates missing tickers by symbol.
    """
    import os
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    updated = 0
    with engine.begin() as conn, open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = {_norm_header(c): c for c in (reader.fieldnames or [])}
        sym = cols.get("symbol") or cols.get("ticker")
        nam = cols.get("name") or cols.get("company")
        if not sym or not nam:
            raise RuntimeError("Names CSV must have Symbol/Ticker and Name/Company")
        for row in reader:
            s = (row.get(sym) or "").strip().upper()
            n = (row.get(nam) or "").strip() or None
            if not s:
                continue
            # Create or update
            tid = conn.execute(text("SELECT id FROM ticker WHERE symbol=:s"), {"s": s}).scalar()
            if tid is None:
                conn.execute(text("INSERT INTO ticker(symbol, name) VALUES (:s, :n)"), {"s": s, "n": n})
            elif n:
                conn.execute(text("UPDATE ticker SET name=COALESCE(name, :n) WHERE id=(SELECT id FROM ticker WHERE symbol=:s)"), {"n": n, "s": s})
            updated += 1
    return updated

def upsert_prices_csv(engine, path: str, chunk: int = 50000) -> int:
    """
    Flexible columns: Symbol/Ticker, Date, Open, High, Low, Close, Volume
    UPSERTS into price_daily with ON CONFLICT (ticker_id, date).
    Safe to rerun; idempotent upserts.
    """
    import os
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    inserted = 0
    with engine.begin() as conn, open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = {_norm_header(c): c for c in (reader.fieldnames or [])}
        sym = cols.get("symbol") or cols.get("ticker")
        dat = cols.get("date") or cols.get("timestamp")
        opn = cols.get("open")
        hig = cols.get("high")
        low = cols.get("low")
        clo = cols.get("close") or cols.get("adjclose") or cols.get("adjustedclose")
        vol = cols.get("volume") or cols.get("vol")
        infer_sym = False
        inferred_value = None
        if not sym:
            # derive symbol from filename if importing per-symbol files
            import os as _os
            inferred_value = _os.path.splitext(_os.path.basename(path))[0].strip().upper()
            if inferred_value:
                infer_sym = True
        if not ((sym or infer_sym) and dat and opn and hig and low and clo and vol):
            raise RuntimeError("Prices CSV must have Symbol, Date, Open, High, Low, Close, Volume")
        buf = []
        def flush():
            nonlocal inserted
            # group by symbol; resolve ticker_id once per symbol
            by_sym = {}
            for r in buf:
                by_sym.setdefault(r["symbol"], []).append(r)
            for s, rows in by_sym.items():
                tid = conn.execute(text("SELECT id FROM ticker WHERE symbol=:s"), {"s": s}).scalar()
                if tid is None:
                    conn.execute(text("INSERT INTO ticker(symbol) VALUES (:s)"), {"s": s})
                    tid = conn.execute(text("SELECT id FROM ticker WHERE symbol=:s"), {"s": s}).scalar()
                for r in rows:
                    conn.execute(text("""
                        INSERT INTO price_daily(ticker_id, date, open, high, low, close, volume)
                        VALUES (:tid, :d, :o, :h, :l, :c, :v)
                        ON CONFLICT (ticker_id, date) DO UPDATE
                        SET open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                            close=EXCLUDED.close, volume=EXCLUDED.volume
                    """), {"tid": tid, **r})
                inserted += len(rows)
            buf.clear()
        for row in reader:
            try:
                s = ((row.get(sym) if sym else inferred_value) or "").strip().upper()
                if not s:
                    continue
                d = _parse_date_flex(str(row.get(dat) or ""))
                o = float(row.get(opn) or 0)
                h = float(row.get(hig) or 0)
                l = float(row.get(low) or 0)
                c = float(row.get(clo) or 0)
                v = int(float(row.get(vol) or 0))
                if c == 0 and o == 0 and h == 0 and l == 0:
                    continue
                buf.append({"symbol": s, "d": d, "o": o, "h": h, "l": l, "c": c, "v": v})
                if len(buf) >= chunk:
                    flush()
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Skipping row error: {e}")
        if buf:
            flush()
    return inserted

# ---- Directory helpers: import all CSVs in a folder ----
def upsert_names_dir(engine, dir_path: str) -> int:
    import os
    total = 0
    for root, _, files in os.walk(dir_path):
        for fn in files:
            if fn.lower().endswith('.csv'):
                total += upsert_names_csv(engine, os.path.join(root, fn))
    return total

def upsert_prices_dir(engine, dir_path: str, chunk: int = 50000) -> int:
    import os
    total = 0
    for root, _, files in os.walk(dir_path):
        for fn in files:
            if fn.lower().endswith('.csv'):
                total += upsert_prices_csv(engine, os.path.join(root, fn), chunk=chunk)
    return total

# ---- CLI helper so I can run this as a script too ----
if __name__ == "__main__":
    # assumes load_dotenv + engine creation already exist in this module
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--import-names", help="CSV path for symbol->name mapping")
    parser.add_argument("--import-prices", help="CSV path for daily prices")
    parser.add_argument("--import-names-dir", help="Directory of CSVs for names")
    parser.add_argument("--import-prices-dir", help="Directory of CSVs for prices")
    args = parser.parse_args()
    engine = create_engine(get_database_url())
    if args.import_names:
        print({"names_updated": upsert_names_csv(engine, args.import_names)})
    if args.import_prices:
        print({"prices_upserted": upsert_prices_csv(engine, args.import_prices)})
    if args.import_names_dir:
        print({"names_updated": upsert_names_dir(engine, args.import_names_dir)})
    if args.import_prices_dir:
        print({"prices_upserted": upsert_prices_dir(engine, args.import_prices_dir)})
