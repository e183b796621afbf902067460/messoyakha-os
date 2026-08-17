from pathlib import Path

import pandas as pd
import polars as pl
from loguru import logger
from skfolio import ExtraRiskMeasure
from skfolio.cluster import HierarchicalClustering, LinkageMethod
from skfolio.model_selection import WalkForward, cross_val_predict
from skfolio.optimization import EqualWeighted, HierarchicalEqualRiskContribution
from skfolio.portfolio import MultiPeriodPortfolio


TRAIN_SIZE = 256
TEST_SIZE = 84


def load_ohlcv(path: Path | str = "ohlcv.parquet") -> pl.DataFrame:
    """Load vertically stored OHLCV observations from a parquet file."""
    return pl.read_parquet(path).filter(pl.col("ticker") != "MCFTRR")


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
            previous = result.index[result.index.get_loc(index) - 1]  # type: ignore[unsupported-operation]
            result.loc[index] = (
                result.loc[previous] * (observed.loc[index] + payout.loc[index]) / observed.loc[previous]
            )
        adjusted[ticker] = result
    return adjusted


def returns(data: pl.DataFrame, dividends: pl.DataFrame | None = None) -> pd.DataFrame:
    """Calculate complete total returns from vertically stored market data."""
    prices = close_prices(data) if dividends is None else adjusted_close_prices(data, dividends)
    result = prices.pct_change(fill_method=None).dropna(how="all").dropna()
    if result.empty:
        raise ValueError("OHLCV data does not contain enough complete price observations.")
    return result


def herc_estimator() -> HierarchicalEqualRiskContribution:
    """Build the HERC estimator used in the walk-forward comparison."""
    return HierarchicalEqualRiskContribution(
        prior_estimator=None,
        risk_measure=ExtraRiskMeasure.ENTROPIC_RISK_MEASURE,
        hierarchical_clustering_estimator=HierarchicalClustering(
            max_clusters=4,
            linkage_method=LinkageMethod.COMPLETE,
        ),
        min_weights=0.05,
        max_weights=1.0,
    )


def walk_forward(
    estimator: EqualWeighted | HierarchicalEqualRiskContribution,
    data: pl.DataFrame,
    dividends: pl.DataFrame | None = None,
) -> MultiPeriodPortfolio:
    """Run walk-forward validation and return the aggregated test portfolio."""
    matrix = returns(data, dividends=dividends)
    splitter = WalkForward(train_size=TRAIN_SIZE, test_size=TEST_SIZE, expand_train=True)
    return cross_val_predict(estimator=estimator, X=matrix, cv=splitter)  # type: ignore[bad-return]


def save_weights(weights: pd.DataFrame, path: Path | str) -> None:
    """Persist walk-forward weights into a parquet file for later analysis."""
    pl.from_pandas(weights.rename_axis("timestamp").reset_index()).write_parquet(path)


def portfolio_metrics(portfolio: MultiPeriodPortfolio) -> dict[str, float]:
    """Compute the performance metrics of a walk-forward portfolio."""
    return {
        "cumulative return": float(portfolio.cumulative_returns[-1]),  # type: ignore[bad-index]
        "mean return": float(portfolio.mean),
        "volatility": float(portfolio.standard_deviation),
        "variance": float(portfolio.variance),
        "sharpe ratio": float(portfolio.sharpe_ratio),
        "sortino ratio": float(portfolio.sortino_ratio),
        "max drawdown": float(portfolio.max_drawdown),
        "calmar ratio": float(portfolio.calmar_ratio),
        "average drawdown": float(portfolio.average_drawdown),
        "worst realization": float(portfolio.worst_realization),
        "value at risk": float(portfolio.value_at_risk),
        "conditional var": float(portfolio.cvar),
        "ulcer index": float(portfolio.ulcer_index),
    }


def compare_metrics(herc: MultiPeriodPortfolio, equal: MultiPeriodPortfolio) -> None:
    """Print the walk-forward metric comparison between HERC and EqualWeighted."""
    comparison = pd.DataFrame(
        {
            "HERC": portfolio_metrics(herc),
            "EqualWeighted": portfolio_metrics(equal),
        }
    )
    logger.info("Walk-forward metrics comparison:\n{}", comparison.round(4))


def run_walk_forward_comparison(
    path: Path | str = "ohlcv.parquet",
    dividends_path: Path | str = "dividends.parquet",
) -> None:
    """Run the walk-forward comparison, persist the weights and print the metrics."""
    ohlcv = load_ohlcv(path)
    dividends = load_ohlcv(dividends_path)

    herc = walk_forward(estimator=herc_estimator(), data=ohlcv, dividends=dividends)
    equal = walk_forward(estimator=EqualWeighted(), data=ohlcv, dividends=dividends)

    save_weights(weights=herc.weights_per_observation, path="walk_forward_weights_herc.parquet")
    save_weights(weights=equal.weights_per_observation, path="walk_forward_weights_equal.parquet")

    compare_metrics(herc=herc, equal=equal)


if __name__ == "__main__":
    run_walk_forward_comparison()
