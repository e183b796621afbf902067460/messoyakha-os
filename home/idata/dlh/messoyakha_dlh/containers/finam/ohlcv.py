from collections.abc import Generator
from datetime import datetime

from dagster import (
    DynamicOut,
    DynamicOutput,
    In,
    JobDefinition,
    Nothing,
    OpExecutionContext,
    graph,
    multiprocess_executor,
    op,
)
from loguru import logger
from polars import DataFrame, col, concat
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_finam_sdk.enums.intervals import FinamIntervalEnum
from messoyakha_finam_sdk.enums.markets import FinamMarketEnum
from messoyakha_finam_sdk.schemas.bars import FinamBarsInputSchema
from messoyakha_finam_sdk.services.finam import FinamMISXService
from messoyakha_sdk.adapters.connections.s3 import options

from messoyakha_dlh.adapters.repositories.finam.ohlcv import FinamOHLCVS3Repository
from messoyakha_dlh.services.finam.ohlcv import FinamOHLCVDLHService, FinamOHLCVDLHSettings


@op(required_resource_keys={"settings", "services"})
def migrate_ohlcv(context: OpExecutionContext) -> None:
    context.resources.settings.catalog.create_namespace_if_not_exists(namespace=context.resources.settings.NAMESPACE)
    if context.resources.settings.catalog.namespace_exists(identifier=context.resources.settings.NAMESPACE):
        context.resources.services["finam_dlh_service"].migrate_ohlcv()


@op(ins={"is_migrated": In(Nothing)}, required_resource_keys={"settings"}, out=DynamicOut())
def tickers(
    context: OpExecutionContext,
) -> Generator[DynamicOutput[tuple[str, FinamMarketEnum, FinamIntervalEnum]], None, None]:
    for ticker, market, interval in context.resources.settings.TICKERS:
        yield DynamicOutput(value=(ticker, market, interval), mapping_key=f"{ticker}_{market}_{interval}")


@op(required_resource_keys={"services"})
def query_latest_timestamp(
    context: OpExecutionContext, item: tuple[str, FinamMarketEnum, FinamIntervalEnum]
) -> datetime:
    ticker, market, interval = item
    latest_timestamp: datetime = context.resources.services["finam_dlh_service"].query_latest_timestamp(
        ticker=ticker, market=market, interval=interval
    )
    logger.info(f"Latest {ticker}-{market}-{interval} timestamp is {latest_timestamp}.")
    return latest_timestamp


@op(required_resource_keys={"services", "settings"})
async def get_ohlcv(
    context: OpExecutionContext, item: tuple[str, FinamMarketEnum, FinamIntervalEnum], latest_timestamp: datetime
) -> DataFrame:
    ticker, market, interval = item
    ohlcv: DataFrame = await context.resources.services["finam_sdk_service"].get_ohlcv(
        input_schema=FinamBarsInputSchema(
            secret=context.resources.settings.FINAM_SECRET,
            ticker=ticker,
            interval=interval,
            start_time=latest_timestamp,
            end_time=context.resources.settings.TRIGGER_DATE,
        )
    )
    ohlcv = ohlcv.filter(col("timestamp") > latest_timestamp)
    logger.info(f"Got {ticker}-{market}-{interval} OHLCV, shape is {ohlcv.shape}.")
    return ohlcv


@op(required_resource_keys={"settings", "services"})
def load_ohlcv(context: OpExecutionContext, data: list[DataFrame]) -> None:
    ohlcv: DataFrame = concat(data)
    logger.info(f"Got all OHLCV to load, shape is {ohlcv.shape}.")
    if not ohlcv.is_empty():
        context.resources.services["finam_dlh_service"].load_ohlcv(ohlcv=ohlcv)


@graph
def process_ticker(item: tuple[str, FinamMarketEnum, FinamIntervalEnum]) -> DataFrame:
    return get_ohlcv(item=item, latest_timestamp=query_latest_timestamp(item=item))


@graph
def finam_ohlcv() -> None:
    load_ohlcv(data=tickers(is_migrated=migrate_ohlcv()).map(process_ticker).collect())


class Container(BaseContainer):
    alias: str | None = "FinamOHLCVContainer"

    settings: Factory[FinamOHLCVDLHSettings] = Factory(FinamOHLCVDLHSettings)
    job: Singleton[JobDefinition] = Singleton(
        finam_ohlcv.to_job,
        name=finam_ohlcv.__name__,  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                finam_sdk_service=Factory(FinamMISXService),
                finam_dlh_service=Factory(  # type: ignore[missing-argument]
                    FinamOHLCVDLHService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        FinamOHLCVS3Repository,
                        options=Factory(  # type: ignore[unexpected-keyword]
                            options,
                            access_key=settings.ACCESS_KEY,
                            secret_key=settings.SECRET_KEY,
                            endpoint=settings.ENDPOINT,
                            region=settings.REGION,
                        ),
                    ),
                ),
            ),
            settings=settings,  # type: ignore[bad-argument-type]
        ),
        executor_def=Factory(  # type: ignore[bad-argument-type]
            multiprocess_executor.configured, config_or_config_fn=Dict(max_concurrent=Factory(lambda: 2))
        ),
        tags=Dict(source=settings.NAMESPACE),  # type: ignore[bad-argument-type]
    )
