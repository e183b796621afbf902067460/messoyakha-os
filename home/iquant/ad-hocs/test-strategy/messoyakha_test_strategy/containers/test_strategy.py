from dagster import JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from polars import DataFrame
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_s3_sdk.adapters.connections.polars import options

from messoyakha_test_strategy.adapters.repositories.cbr.key_rates import CBRKeyRatesS3Repository
from messoyakha_test_strategy.adapters.repositories.dohod.dividends import DohodDividendsS3Repository
from messoyakha_test_strategy.adapters.repositories.fedstat.inflation_rates import FedstatInflationRatesS3Repository
from messoyakha_test_strategy.adapters.repositories.finam.ohlcv import FinamOHLCVS3Repository
from messoyakha_test_strategy.services.test_strategy import merge
from messoyakha_test_strategy.settings import TestStrategySettings


@op(required_resource_keys={"settings", "services"})
def query_ohlcv(context: OpExecutionContext) -> DataFrame:
    ohlcv: DataFrame = context.resources.services["ohlcv_repository"].read_ohlcv(
        catalog=context.resources.settings.catalog,
        namespace=context.resources.settings.NAMESPACE,
        ticker=context.resources.settings.TICKER,
        market=context.resources.settings.MARKET,
        interval=context.resources.settings.INTERVAL,
    )
    logger.info(
        f"Got OHLCV for {context.resources.settings.TICKER}-{context.resources.settings.MARKET}-{context.resources.settings.INTERVAL}, shape is {ohlcv.shape}."
    )
    return ohlcv


@op(required_resource_keys={"settings", "services"})
def query_dividends(context: OpExecutionContext) -> DataFrame:
    dividends: DataFrame = context.resources.services["dividends_repository"].read_dividends(
        catalog=context.resources.settings.catalog,
        namespace=context.resources.settings.NAMESPACE,
        ticker=context.resources.settings.TICKER,
    )
    logger.info(f"Got dividends for {context.resources.settings.TICKER}, shape is {dividends.shape}.")
    return dividends


@op(required_resource_keys={"settings", "services"})
def query_key_rates(context: OpExecutionContext) -> DataFrame:
    key_rates: DataFrame = context.resources.services["key_rates_repository"].read_key_rates(
        catalog=context.resources.settings.catalog,
        namespace=context.resources.settings.NAMESPACE,
    )
    logger.info(f"Got key rates, shape is {key_rates.shape}.")
    return key_rates


@op(required_resource_keys={"settings", "services"})
def query_inflation_rates(context: OpExecutionContext) -> DataFrame:
    inflation_rates: DataFrame = context.resources.services["inflation_rates_repository"].read_inflation_rates(
        catalog=context.resources.settings.catalog,
        namespace=context.resources.settings.NAMESPACE,
    )
    logger.info(f"Got inflation rates, shape is {inflation_rates.shape}.")
    return inflation_rates


@op
def final(
    ohlcv: DataFrame,
    dividends: DataFrame,
    key_rates: DataFrame,
    inflation_rates: DataFrame,
) -> None:
    merged: DataFrame = merge(ohlcv=ohlcv, dividends=dividends, key_rates=key_rates, inflation_rates=inflation_rates)
    merged.write_csv("data.csv")
    logger.info(f"Merged dataframe shape is {merged.shape}.")


@graph
def test_strategy() -> None:
    final(
        ohlcv=query_ohlcv(),
        dividends=query_dividends(),
        key_rates=query_key_rates(),
        inflation_rates=query_inflation_rates(),
    )


class Container(BaseContainer):
    alias: str | None = "TestStrategyContainer"

    settings: Factory[TestStrategySettings] = Factory(TestStrategySettings)
    job: Singleton[JobDefinition] = Singleton(
        test_strategy.to_job,
        name=test_strategy.__name__,  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                ohlcv_repository=Factory(  # type: ignore[missing-argument]
                    FinamOHLCVS3Repository,
                    options=Factory(  # type: ignore[unexpected-keyword]
                        options,
                        access_key=settings.ACCESS_KEY,
                        secret_key=settings.SECRET_KEY,
                        endpoint=settings.ENDPOINT,
                        region=settings.REGION,
                    ),
                ),
                dividends_repository=Factory(  # type: ignore[missing-argument]
                    DohodDividendsS3Repository,  # type: ignore[bad-argument-type]
                    options=Factory(  # type: ignore[unexpected-keyword]
                        options,
                        access_key=settings.ACCESS_KEY,
                        secret_key=settings.SECRET_KEY,
                        endpoint=settings.ENDPOINT,
                        region=settings.REGION,
                    ),
                ),
                key_rates_repository=Factory(  # type: ignore[missing-argument]
                    CBRKeyRatesS3Repository,  # type: ignore[bad-argument-type]
                    options=Factory(  # type: ignore[unexpected-keyword]
                        options,
                        access_key=settings.ACCESS_KEY,
                        secret_key=settings.SECRET_KEY,
                        endpoint=settings.ENDPOINT,
                        region=settings.REGION,
                    ),
                ),
                inflation_rates_repository=Factory(  # type: ignore[missing-argument]
                    FedstatInflationRatesS3Repository,  # type: ignore[bad-argument-type]
                    options=Factory(  # type: ignore[unexpected-keyword]
                        options,
                        access_key=settings.ACCESS_KEY,
                        secret_key=settings.SECRET_KEY,
                        endpoint=settings.ENDPOINT,
                        region=settings.REGION,
                    ),
                ),
            ),
            settings=settings,  # type: ignore[bad-argument-type]
        ),
        tags=Dict(source=settings.NAMESPACE),  # type: ignore[bad-argument-type]
    )
