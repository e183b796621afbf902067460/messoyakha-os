from collections.abc import Generator
from datetime import datetime

from dagster import DynamicOut, DynamicOutput, JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from nautilus_trader.model.currencies import RUB
from polars import DataFrame, col, concat
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_finam_sdk.enums.intervals import FinamIntervalEnum
from messoyakha_finam_sdk.schemas.bars import FinamBarsMISXSpotInputSchema
from messoyakha_finam_sdk.services.finam import FinamMISXSpotService
from messoyakha_moex_iss_sdk.schemas.listed_from import MOEXListedFromInputSchema
from messoyakha_moex_iss_sdk.services.moex import MOEXStockSharesService
from messoyakha_sdk.adapters.venues.misx import MISX
from messoyakha_sdk.enums.venues.misx import MISXProductEnum
from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema

from messoyakha_dlh.adapters.repositories.finam import FinamS3Repository
from messoyakha_dlh.schemas.finam import FinamOHLCVSchema
from messoyakha_dlh.services.finam import FinamDLHService
from messoyakha_dlh.settings import DLHSettings


class _FinamOHLCVDLHSettings(DLHSettings):
    TICKERS: list[tuple[str, FinamIntervalEnum, str]] = [
        ("SIBN", FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("NVTK", FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("TRNFP", FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("PHOR", FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("PLZL", FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("SBER", FinamIntervalEnum.ONE_DAY, str(RUB)),
    ]
    FINAM_SECRET: str


@op(required_resource_keys={"settings"}, out=DynamicOut())
def tickers(
    context: OpExecutionContext,
) -> Generator[DynamicOutput[tuple[str, FinamIntervalEnum, str]], None, None]:
    for ticker, interval, currency in context.resources.settings.TICKERS:
        yield DynamicOutput(value=(ticker, interval, currency), mapping_key=f"{ticker}_{interval}_{currency}")


@op(required_resource_keys={"services"})
async def query_latest_ohlcv_timestamp(
    context: OpExecutionContext, item: tuple[str, FinamIntervalEnum, str]
) -> datetime:
    ticker, interval, currency = item
    latest_timestamp: datetime | None = context.resources.services["finam_dlh_service"].query_latest_ohlcv_timestamp(
        ticker=ticker,
        venue=MISX,
        product=MISXProductEnum.SPOT.value,
        currency=currency,
        interval=interval,
    )
    if not latest_timestamp:
        logger.info(f"Got no latest timestamp for {ticker}-{interval}-{currency}, querying MOEX ISS.")
        latest_timestamp = await context.resources.services["moex_iss_sdk_service"].get_first_trade_date(
            input_schema=MOEXListedFromInputSchema(ticker=ticker)
        )
    logger.info(f"Latest {ticker}-{interval}-{currency} timestamp is {latest_timestamp}.")
    return latest_timestamp


@op(required_resource_keys={"services", "settings"})
async def get_ohlcv(
    context: OpExecutionContext, item: tuple[str, FinamIntervalEnum, str], latest_timestamp: datetime
) -> DataFrame:
    ticker, interval, currency = item
    ohlcv: DataFrame = await context.resources.services["finam_sdk_service"].get_ohlcv(
        input_schema=FinamBarsMISXSpotInputSchema(
            secret=context.resources.settings.FINAM_SECRET,
            ticker=ticker,
            interval=interval,
            currency=currency,
            start_time=latest_timestamp,
            end_time=context.resources.settings.TRIGGER_DATE,
        )
    )
    ohlcv = ohlcv.filter(col("timestamp") > latest_timestamp)
    ohlcv = ohlcv.with_columns(
        year=col("timestamp").dt.year(),
        month=col("timestamp").dt.month(),
    )
    logger.info(f"Got {ticker}-{interval}-{currency} OHLCV, shape is {ohlcv.shape}.")
    return ohlcv


@op(required_resource_keys={"settings", "services"})
def load_ohlcv(context: OpExecutionContext, data: list[DataFrame]) -> None:
    ohlcv: DataFrame = concat(data)
    logger.info(f"Got all OHLCV to load, shape is {ohlcv.shape}.")
    if not ohlcv.is_empty():
        ohlcv = ohlcv.with_columns(
            _partition_by_ticker=col("ticker"),
            _partition_by_interval=col("interval"),
            _partition_by_product=col("product"),
            _partition_by_venue=col("venue"),
            _partition_by_currency=col("currency"),
            _partition_by_year=col("year"),
            _partition_by_month=col("month"),
        ).pipe(FinamOHLCVSchema.validate)
        logger.info(f"OHLCV shape is {ohlcv.shape}.")

        context.resources.services["finam_dlh_service"].load_to_dlh(
            data=ohlcv,
            path="s3://f8e90488-f511555d-274b-4258-bffc-572dd1900382/finam/ohlcv/",
            partitions=[
                "_partition_by_ticker",
                "_partition_by_interval",
                "_partition_by_product",
                "_partition_by_venue",
                "_partition_by_currency",
                "_partition_by_year",
                "_partition_by_month",
            ],
        )


@graph
def process_ticker(item: tuple[str, FinamIntervalEnum, str]) -> DataFrame:
    return get_ohlcv(item=item, latest_timestamp=query_latest_ohlcv_timestamp(item=item))


@graph
def finam_ohlcv() -> None:
    load_ohlcv(data=tickers().map(process_ticker).collect())


class Container(BaseContainer):
    settings: Factory[_FinamOHLCVDLHSettings] = Factory(_FinamOHLCVDLHSettings)
    job: Singleton[JobDefinition] = Singleton(
        finam_ohlcv.to_job,
        name=Factory(lambda: finam_ohlcv.__name__),  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                finam_sdk_service=Factory(FinamMISXSpotService),
                moex_iss_sdk_service=Factory(MOEXStockSharesService),  # type: ignore[bad-argument-type]
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
