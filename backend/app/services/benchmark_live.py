from datetime import date, timedelta
from zoneinfo import ZoneInfo
from yahoo_fin import stock_info as si

NY = ZoneInfo("America/New_York")

def _prev_weekday(d):
    while d.weekday() > 4:  # Monday=0, Sunday=6
        d -= timedelta(days=1)
    return d

def get_last_business_day_prices(symbol):
    """
    Returns (last_business_day, close, prev_close)
    for indexes like SPY, QQQ, DIA using yahoo_fin.
    """
    try:
        # Get the last 5 days of historical prices
        df = si.get_data(symbol, interval="1d")
        if df.empty or len(df) < 2:
            return None
        # Take the last two trading days
        last_date = df.index[-1].date()
        prev_date = df.index[-2].date()
        close = float(df["close"].iloc[-1])
        prev_close = float(df["close"].iloc[-2])
        return last_date.isoformat(), close, prev_close
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None
