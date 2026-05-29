from polars import DataFrame, col


def merge(
    ohlcv: DataFrame,
    dividends: DataFrame,
    key_rates: DataFrame,
    inflation_rates: DataFrame,
) -> DataFrame:
    ohlcv = ohlcv.with_columns(col("timestamp").dt.date().alias("date"))
    dividends = dividends.with_columns(col("timestamp").dt.date().alias("date"))
    key_rates = key_rates.with_columns(col("timestamp").dt.date().alias("date"))
    inflation_rates = inflation_rates.with_columns(col("timestamp").dt.date().alias("date"))

    min_date = min(
        ohlcv.select(col("date").min()).item(),
        key_rates.select(col("date").min()).item(),
        inflation_rates.select(col("date").min()).item(),
    )

    ohlcv = ohlcv.filter(col("date") >= min_date)
    key_rates = key_rates.filter(col("date") >= min_date)
    inflation_rates = inflation_rates.filter(col("date") >= min_date)

    base = ohlcv.select(["ticker", "timestamp", "date", "open", "high", "low", "close", "volume"]).sort("date")
    result = base.join(dividends, on=["ticker", "date"], how="left")

    key_rates_sorted = key_rates.select(["date", "key_rate"]).sort("date")
    result = result.join_asof(key_rates_sorted, on="date", strategy="backward")

    inflation_rates_sorted = inflation_rates.select(["date", "inflation_rate"]).sort("date")
    result = result.join_asof(inflation_rates_sorted, on="date", strategy="backward")

    return result.drop("timestamp_right")
