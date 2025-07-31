import pandas as pd
import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from config.CONFIG import bi_api_key, bi_sec_key

BASE_URL = "https://api.binance.com"



import pandas as pd
import requests
from datetime import datetime
import time

BASE_URL = "https://api.binance.com"

def fetch_single_crypto_period_binance(
    symbol: str,
    interval: str = "1d",          # valid: '1m','3m','5m','15m','30m','1h','2h','4h','6h','8h','12h','1d','3d','1w','1M'
    start: str = None,             # format 'YYYY-MM-DD' ou None
    end: str = None,               # format 'YYYY-MM-DD' ou None
    limit: int = 1000,             # max 1000 per request (Binance limit)
    write_csv: bool = True,
    csv_filename: str = None
) -> pd.DataFrame:
    """
    Fetch historical OHLCV (Open, High, Low, Close, Volume) data for a crypto symbol on Binance.

    Params:
    - symbol: Trading pair, e.g. "BTCUSDT"
    - interval: Kline interval string
    - start: Start date string 'YYYY-MM-DD' or None
    - end: End date string 'YYYY-MM-DD' or None
    - limit: Max number of data points per request (Binance max 1000)
    - write_csv: Save to CSV if True
    - csv_filename: filename for CSV output

    Returns:
    - pd.DataFrame with columns ['open_time', 'open', 'high', 'low', 'close', 'volume', ...] with datetime index
    """

    endpoint = "/api/v3/klines"
    headers = {"Accept": "application/json"}

    # Convert start and end dates to timestamps in ms
    def to_millis(dt_str):
        return int(datetime.strptime(dt_str, "%Y-%m-%d").timestamp() * 1000)

    start_ts = to_millis(start) if start else None
    end_ts = to_millis(end) if end else None

    all_klines = []
    fetch_start = start_ts

    while True:
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }
        if fetch_start:
            params["startTime"] = fetch_start
        if end_ts:
            params["endTime"] = end_ts

        resp = requests.get(f"{BASE_URL}{endpoint}", params=params, headers=headers)
        if resp.status_code != 200:
            print(f"Error fetching data: {resp.status_code} {resp.text}")
            break

        data = resp.json()
        if not data:
            break

        all_klines.extend(data)

        # Binance returns up to limit candles starting from startTime
        last_open_time = data[-1][0]
        # next fetch start = last open time + 1 ms to avoid overlap
        fetch_start = last_open_time + 1

        # If less than limit candles returned, no more data
        if len(data) < limit:
            break

        # Avoid hitting rate limit
        time.sleep(0.2)

    if not all_klines:
        print(f"No data found for {symbol} with given parameters.")
        return pd.DataFrame()

    # Format columns based on Binance Klines API doc
    df = pd.DataFrame(all_klines, columns=[
        "symbol","open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
    ])

    # Convert timestamps to datetime
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
    df["symbol"]=symbol
    # Set open_time as index
    df.set_index("open_time", inplace=True)

    # Convert numeric columns to float
    float_cols = ["open", "high", "low", "close", "volume", "quote_asset_volume",
                  "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume"]
    df[float_cols] = df[float_cols].astype(float)

    # Drop columns you may not need
    df.drop(columns=["ignore"], inplace=True)

    if write_csv:
        if not csv_filename:
            csv_filename = f"{symbol}_{interval}_{start}_{end}.csv"
        df.to_csv(csv_filename)
        print(f"Data saved to {csv_filename}")

    return df

# df = fetch_single_crypto_period_binance("BTCUSDT", interval="1d", start="2023-01-01", end="2025-03-01")



def fetch_crypto_current_binance(
    symbols: list[str],
    write_csv: bool = True
) -> pd.DataFrame:
    """
    Fetch current ticker information for a list of crypto trading pairs using Binance API.

    Parameters:
    - symbols: List of trading pairs (e.g., ['BTCUSDT', 'ETHUSDT']).
    - write_csv: If True, saves the resulting DataFrame to 'binance_crypto_record.csv'.

    Returns:
    - pandas DataFrame with columns:
      ['symbol', 'price', 'high_price', 'low_price', 'volume', 'quote_volume', 'price_change_percent']

    Notes:
    - This uses Binance's public ticker endpoints (no signature required).
    """
    endpoint = "/api/v3/ticker/24hr"
    records = []

    for symbol in symbols:
        try:
            url = f"{BASE_URL}{endpoint}?symbol={symbol.upper()}"
            resp = requests.get(url)
            if resp.status_code != 200:
                print(f"Error fetching {symbol}: {resp.status_code}")
                continue
            data = resp.json()
            records.append({
                "symbol": data["symbol"],
                "price": float(data["lastPrice"]),
                "high_price": float(data["highPrice"]),
                "low_price": float(data["lowPrice"]),
                "volume": float(data["volume"]),
                "quote_volume": float(data["quoteVolume"]),
                "price_change_percent": float(data["priceChangePercent"])
            })
        except Exception as e:
            print(f"Failed to fetch data for {symbol}: {e}")

    df = pd.DataFrame(records)

    if write_csv:
        df.to_csv("binance_crypto_record.csv", index=False)
        print("Data saved to binance_crypto_record.csv")

    return df

# Example usage
# symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
# # df = fetch_crypto_current_binance(symbols)
# print(df.head())
