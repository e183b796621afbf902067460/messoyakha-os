import time
from datetime import datetime
import pandas as pd
from hyperliquid.info import Info
from hyperliquid.utils import constants
from pathlib import Path
from json import loads


config: Path = Path("/home/spuchin/GitHub/candlesticks-pipelines/src/entrypoints/tests/config.json")
config: dict[str, str] = loads(config.read_text(encoding='utf-8'))


def get_1s_candlesticks_sdk(symbol="ETH", start_time_ms=None):
    """
    Download 1-second candlesticks from Hyperliquid using the official SDK.

    Args:
        symbol (str): Trading pair symbol (e.g., "ETH", "BTC") - Base asset name only
        limit (int): Number of candles to retrieve
        start_time_ms (int): Start timestamp in milliseconds (optional)

    Returns:
        list: List of candlestick data
    """
    # Initialize the Info client without WebSocket
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    # Validate interval
    interval = "1m"  # Fixed for 1-second candles

    # Fetch candlesticks using the SDK
    # Note: The SDK's query_candle_snapshot method takes coin name (like "ETH"), interval, startTime, endTime
    end_time_ms = int(time.time() * 1000) if not start_time_ms else None
    candle_data = info.candles_snapshot(
        name=symbol,
        interval=interval,
        startTime=start_time_ms,
        endTime=end_time_ms
    )

    if candle_data is None:
        print("Received no data from API")
        return []

    return candle_data


def candlesticks_to_dataframe(candles, symbol="ETH"):
    """
    Convert raw candlestick data from SDK to a pandas DataFrame.

    Args:
        candles (list): Raw candlestick data from SDK
        symbol (str): Trading pair symbol (base asset)

    Returns:
        pd.DataFrame: DataFrame with candlestick data
    """
    if not candles:
        return pd.DataFrame()

    # Convert raw candlestick data to structured format
    df_data = []
    for candle in candles:
        # SDK returns candle data as: [T, o, h, l, c, v]
        # T: timestamp (ms), o: open, h: high, l: low, c: close, v: volume
        timestamp = datetime.fromtimestamp(candle["t"] / 1000)  # Convert ms to s
        open_price = float(candle["o"])
        high_price = float(candle["h"])
        low_price = float(candle["l"])
        close_price = float(candle["c"])
        volume = float(candle["v"])

        df_data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume,
            'symbol': f"{symbol}/USD"  # Assuming USD as quote currency
        })

    # Create DataFrame
    df = pd.DataFrame(df_data)
    df.sort_values("timestamp", inplace=True)

    return df


def load_candlesticks_to_dataframe_sdk(symbol="ETH", limit=5000):
    """
    Load 1-second candlesticks from Hyperliquid using the SDK and return as a pandas DataFrame.

    Args:
        symbol (str): Trading pair symbol (base asset like "ETH")
        limit (int): Number of candles to retrieve

    Returns:
        pd.DataFrame: DataFrame containing candlestick data
    """
    print(f"Loading 1s candlesticks for {symbol}/USD using Hyperliquid SDK...")

    # Calculate start time (limit seconds ago) in milliseconds
    start_time_ms = int(datetime(year=2026, month=1, day=19).timestamp() * 1000)

    # Fetch candlesticks using SDK
    raw_candles = get_1s_candlesticks_sdk(
        symbol=symbol,
        start_time_ms=start_time_ms
    )

    if not raw_candles:
        print("Failed to retrieve candlesticks")
        return pd.DataFrame()

    # Convert to DataFrame
    df = candlesticks_to_dataframe(raw_candles, symbol)

    print(f"Successfully loaded {len(df)} candlesticks for {symbol}/USD")
    return df


# Example usage
if __name__ == "__main__":
    # Load 1s candlesticks for ETH/USD into a DataFrame using the SDK
    symbol = "ETH"  # Base asset name only
    limit = 100  # Number of candles to fetch

    # Load data into DataFrame using SDK
    df = load_candlesticks_to_dataframe_sdk(symbol, limit)

    if not df.empty:
        print(f"\nDataFrame shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"Date range: {df.index.min()} to {df.index.max()}")

        # Save to CSV file
        filename = f"{symbol}_USD_1s_candles.csv"
        df.to_csv(filename)