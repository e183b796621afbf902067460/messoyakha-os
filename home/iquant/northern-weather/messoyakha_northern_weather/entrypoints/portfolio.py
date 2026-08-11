from pathlib import Path

import pandas as pd
import polars as pl
from loguru import logger
from skfolio import ExtraRiskMeasure
from skfolio.cluster import HierarchicalClustering, LinkageMethod
from skfolio.optimization import HierarchicalEqualRiskContribution
from skfolio.prior import EmpiricalPrior
from skfolio.model_selection import WalkForward
from skfolio.metrics


DEFAULT_WINDOW = 756


def load_ohlcv(path: Path | str = "ohlcv.parquet") -> pl.DataFrame:
    """Load vertically stored OHLCV observations from a parquet file."""
    return pl.read_parquet(path)


def close_prices(data: pl.DataFrame) -> pd.DataFrame:
    """Pivot close prices into a date-indexed matrix with one column per ticker."""
    ticker = "ticker" if "ticker" in data.columns else "_partition_by_ticker"
    prices = (
        data.select(  # noqa: PD010
            pl.col("timestamp").cast(pl.Date),
            pl.col(ticker).alias("ticker"),
            pl.col("close").cast(pl.Float64),
        )
        .drop_nulls(["timestamp", "ticker", "close"])
        .group_by(["timestamp", "ticker"])
        .agg(pl.col("close").last())
        .pivot(index="timestamp", on="ticker", values="close")
        .sort("timestamp")
    )
    return pd.DataFrame(prices.to_dicts()).set_index("timestamp")


def dividend_amounts(data: pl.DataFrame) -> pd.DataFrame:
    """Pivot vertically stored dividends into a date-indexed ticker matrix."""
    ticker = "ticker" if "ticker" in data.columns else "_partition_by_ticker"
    dividends = (
        data.select(  # noqa: PD010
            pl.col("timestamp").cast(pl.Date),
            pl.col(ticker).alias("ticker"),
            pl.col("dividend").cast(pl.Float64),
        )
        .drop_nulls(["timestamp", "ticker", "dividend"])
        .group_by(["timestamp", "ticker"])
        .agg(pl.col("dividend").sum())
        .pivot(index="timestamp", on="ticker", values="dividend")
        .sort("timestamp")
    )
    return pd.DataFrame(dividends.to_dicts()).set_index("timestamp")


def adjusted_close_prices(ohlcv: pl.DataFrame, dividends: pl.DataFrame) -> pd.DataFrame:
    """Build close prices whose returns include cash dividends."""
    prices = close_prices(ohlcv)
    payouts = dividend_amounts(dividends).reindex(index=prices.index, columns=prices.columns, fill_value=0.0)
    payouts = payouts.fillna(0.0)
    adjusted = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    for ticker in prices.columns:
        observed = prices[ticker].dropna()
        payout = payouts[ticker].reindex(observed.index, fill_value=0.0)
        result = observed.copy()
        for index in observed.index[1:]:
            previous = result.index[result.index.get_loc(index) - 1]
            result.loc[index] = result.loc[previous] * (observed.loc[index] + payout.loc[index]) / observed.loc[previous]
        adjusted[ticker] = result
    return adjusted


def returns(
    data: pl.DataFrame,
    dividends: pl.DataFrame | None = None,
    window: int = DEFAULT_WINDOW,
) -> pd.DataFrame:
    """Calculate complete total returns from vertically stored market data."""
    prices = close_prices(data) if dividends is None else adjusted_close_prices(data, dividends)
    result = prices.pct_change(fill_method=None).dropna(how="all").dropna().tail(window)
    if result.empty:
        raise ValueError("OHLCV data does not contain enough complete price observations.")
    return result


def portfolio_weights(
    data: pl.DataFrame,
    dividends: pl.DataFrame | None = None,
    window: int = DEFAULT_WINDOW,
) -> pd.Series:
    """Fit HERC to OHLCV returns and return a ticker-to-weight series."""
    matrix = returns(data, dividends=dividends, window=window)
    model = HierarchicalEqualRiskContribution(
        prior_estimator=None,
        risk_measure=ExtraRiskMeasure.VALUE_AT_RISK,
        hierarchical_clustering_estimator=HierarchicalClustering(
            max_clusters=2,
            linkage_method=LinkageMethod.CENTROID
        ),
        min_weights=0.0,
        max_weights=1.0,
    )
    model.fit(matrix)
    return pd.Series(model.weights_, index=matrix.columns, name="weight").sort_values(ascending=False)


def build_portfolio_weights(
    path: Path | str = "ohlcv.parquet",
    dividends_path: Path | str = "dividends.parquet",
    window: int = DEFAULT_WINDOW,
) -> pd.Series:
    """Load OHLCV data and calculate HERC portfolio weights."""
    return portfolio_weights(
        load_ohlcv(path),
        dividends=load_ohlcv(dividends_path),
        window=window,
    )


if __name__ == "__main__":
    logger.info("Portfolio weights:\n{}", build_portfolio_weights())
