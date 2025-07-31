import yfinance as yf
import pandas as pd

def fetch_single_stock_period(
    symbol: str,
    period: str = "1mo",         # valid: '1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','max'
    interval: str = "1d",        # valid: '1m','2m','5m','15m','30m','60m','90m','1h','1d','5d','1wk','1mo','3mo'
    start: str = None,           # format 'YYYY-MM-DD'
    end: str = None,             # format 'YYYY-MM-DD'
    auto_adjust: bool = True,    # adjust OHLC prices for dividends and splits
    actions: bool = True,        # include dividends and splits
    write_csv: bool = True,
    csv_filename: str = None
) -> pd.DataFrame:
    """
    Fetch historical stock data for a single stock symbol.

    Parameters:
    - symbol: Stock ticker symbol (e.g., "AAPL" for Apple).
    - period: Data period to download (e.g., '1mo' for one month). Overrides start/end if specified.
    - interval: Data frequency (e.g., '1d' for daily, '1m' for 1-minute).
    - start: Start date for data retrieval (format 'YYYY-MM-DD'). Optional if period is specified.
    - end: End date for data retrieval (format 'YYYY-MM-DD'). Optional if period is specified.
    - auto_adjust: If True, adjusts OHLC prices for dividends and splits.
    - actions: If True, includes dividend and stock split data.
    - write_csv: If True, saves the resulting DataFrame to CSV.
    - csv_filename: Filename for CSV output. Defaults to "<symbol>_<period>_<interval>.csv".

    Returns:
    - pandas DataFrame containing the historical stock data with datetime index.

    Notes:
    - If no data is found for the given parameters, prints a warning and returns an empty DataFrame.
    """
    ticker = yf.Ticker(symbol)
    data = ticker.history(
        period=period,
        interval=interval,
        start=start,
        end=end,
        auto_adjust=auto_adjust,
        actions=actions
    )
    if data.empty:
        print(f"No data found for {symbol} with the specified parameters.")
        return data

    if write_csv:
        if csv_filename is None:
            csv_filename = f"{symbol}_{period}_{interval}.csv"
        data.to_csv(csv_filename,sep=";")
        print(f"Data saved to {csv_filename}")

    return data

### Example usage :

# df = fetch_single_stock_period(
#     symbol="AAPL",          # Stock symbol for Apple
#     period="3mo",           # Last 3 months data
#     interval="1d",          # Daily frequency
#     auto_adjust=True,       # Adjust prices for dividends and splits
#     csv_filename="apple_stock_data.csv"
# )



def fetch_stock_current(
        symbols: list[str],
        write_csv: bool = True,
        csv_filename= "record.csv"
    ) -> pd.DataFrame:
    """
    Fetch current price and key details for a list of stock symbols.

    Parameters:
    - symbols: List of stock ticker symbols (e.g., ['AAPL', 'MSFT']).
    - write_csv: If True, saves the resulting DataFrame to 'record.csv'.

    Returns:
    - pandas DataFrame with columns:
      ['symbol', 'current_price', 'previous_close', 'open', 'day_high', 'day_low', 'volume', 'market_cap']

    Notes:
    - Symbols that cannot be fetched will be skipped with an error printed.
    - The output CSV 'record.csv' is overwritten each time write_csv is True.
    """
    records = []
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            record = {
                "symbol": symbol,
                "current_price": info.get("regularMarketPrice"),
                "previous_close": info.get("previousClose"),
                "open": info.get("open"),
                "day_high": info.get("dayHigh"),
                "day_low": info.get("dayLow"),
                "volume": info.get("volume"),
                "market_cap": info.get("marketCap"),
            }
            records.append(record)
        except Exception as e:
            print(f"Failed to fetch data for {symbol}: {e}")

    df = pd.DataFrame(records)

    if write_csv:
        df.to_csv(csv_filename, index=False,sep=";")
        print(f"Data saved to {csv_filename}")

    return df

# Example usage
# symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
# current_data = fetch_stock_current(symbols)
