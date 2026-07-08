from collections.abc import Generator
from datetime import datetime, timezone

from dagster import DynamicOut, DynamicOutput, JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from polars import DataFrame, col, concat
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_finam_sdk.enums.intervals import FinamIntervalEnum
from messoyakha_finam_sdk.enums.markets import FinamMarketEnum
from messoyakha_finam_sdk.schemas.bars import FinamBarsInputSchema
from messoyakha_finam_sdk.services.finam import FinamMISXService
from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema

from messoyakha_dlh.adapters.repositories.finam import FinamS3Repository
from messoyakha_dlh.schemas.finam import FinamOHLCVSchema
from messoyakha_dlh.services.finam import FinamDLHService
from messoyakha_dlh.settings import DLHSettings


class FinamDLHSettings(DLHSettings):
    CATCH_UP_DATE: datetime = datetime(year=2011, month=1, day=1, tzinfo=timezone.utc)
    TICKERS: list[tuple[str, FinamMarketEnum, FinamIntervalEnum]] = [
        ("SIBN", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("GAZP", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("NVTK", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("TRNFP", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("PHOR", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("PLZL", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("SBER", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
    ]
    FINAM_SECRET: str


@op(required_resource_keys={"settings"}, out=DynamicOut())
def tickers(
    context: OpExecutionContext,
) -> Generator[DynamicOutput[tuple[str, FinamMarketEnum, FinamIntervalEnum]], None, None]:
    for ticker, market, interval in context.resources.settings.TICKERS:
        yield DynamicOutput(value=(ticker, market, interval), mapping_key=f"{ticker}_{market}_{interval}")


@op(required_resource_keys={"services", "settings"})
def query_latest_ohlcv_timestamp(
    context: OpExecutionContext, item: tuple[str, FinamMarketEnum, FinamIntervalEnum]
) -> datetime:
    ticker, market, interval = item
    latest_timestamp: datetime = context.resources.services["finam_dlh_service"].query_latest_ohlcv_timestamp(
        ticker=ticker, market=market, interval=interval, catch_up_date=context.resources.settings.CATCH_UP_DATE
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
    ohlcv = ohlcv.with_columns(
        year=col("timestamp").dt.year(),
        month=col("timestamp").dt.month(),
    )
    logger.info(f"Got {ticker}-{market}-{interval} OHLCV, shape is {ohlcv.shape}.")
    return ohlcv


@op(required_resource_keys={"settings", "services"})
def load_ohlcv(context: OpExecutionContext, data: list[DataFrame]) -> None:
    ohlcv: DataFrame = concat(data)
    logger.info(f"Got all OHLCV to load, shape is {ohlcv.shape}.")
    if not ohlcv.is_empty():
        ohlcv = ohlcv.with_columns(
            _partition_by_ticker=col("ticker"),
            _partition_by_market=col("market"),
            _partition_by_interval=col("interval"),
            _partition_by_year=col("year"),
            _partition_by_month=col("month"),
        )
        ohlcv = FinamOHLCVSchema.validate(ohlcv)
        logger.info(f"OHLCV shape is {ohlcv.shape}.")

        context.resources.services["finam_dlh_service"].load_to_dlh(
            data=ohlcv,
            path="s3://f8e90488-f511555d-274b-4258-bffc-572dd1900382/finam/ohlcv/",
            partitions=[
                "_partition_by_ticker",
                "_partition_by_market",
                "_partition_by_interval",
                "_partition_by_year",
                "_partition_by_month",
            ],
        )


@graph
def process_ticker(item: tuple[str, FinamMarketEnum, FinamIntervalEnum]) -> DataFrame:
    return get_ohlcv(item=item, latest_timestamp=query_latest_ohlcv_timestamp(item=item))


@graph
def finam_ohlcv() -> None:
    load_ohlcv(data=tickers().map(process_ticker).collect())


class Container(BaseContainer):
    settings: Factory[FinamDLHSettings] = Factory(FinamDLHSettings)
    job: Singleton[JobDefinition] = Singleton(
        finam_ohlcv.to_job,
        name=Factory(lambda: finam_ohlcv.__name__),  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                finam_sdk_service=Factory(FinamMISXService),
                finam_dlh_service=Factory(  # type: ignore[missing-argument]
                    FinamDLHService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        FinamS3Repository,
                        options=Factory(  # type: ignore[unexpected-keyword]
                            S3StorageOptionsSchema,
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
    )
