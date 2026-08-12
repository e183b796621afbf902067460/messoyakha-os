from collections.abc import Generator
from datetime import datetime

from dagster import DynamicOut, DynamicOutput, JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from nautilus_trader.model.currencies import RUB
from polars import DataFrame, col, concat
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_finam_sdk.enums.intervals import (
    FinamIntervalEnum,
    finam_to_messoyakha_interval,
    finam_to_messoyakha_interval_mapping,
)
from messoyakha_moex_iss_sdk.enums.intervals import (
    MOEXIntervalEnum,
    moex_iss_to_messoyakha_interval,
    moex_iss_to_messoyakha_interval_mapping,
)
from messoyakha_sdk.adapters.venues.misx import MISX
from messoyakha_sdk.enums.venues.misx import MISXProductEnum
from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema

from messoyakha_dlh.adapters.repositories.finam import FinamS3Repository
from messoyakha_dlh.adapters.repositories.moex_iss import MOEXISSS3Repository
from messoyakha_dlh.services.finam import FinamDLHService
from messoyakha_dlh.services.moex_iss import MOEXISSDLHService
from messoyakha_dwh.adapters.repositories.ohlcv import OHLCVS3Repository
from messoyakha_dwh.schemas.ohlcv import OHLCVSchema
from messoyakha_dwh.services.ohlcv import OHLCVService
from messoyakha_dwh.settings import DWHSettings


class _OHLCVDWHSettings(DWHSettings):
    FINAM_TICKERS: list[tuple[str, str, FinamIntervalEnum, str]] = [
        ("SIBN", MISX, FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("NVTK", MISX, FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("TRNFP", MISX, FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("RAGR", MISX, FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("PHOR", MISX, FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("PLZL", MISX, FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("GMKN", MISX, FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("CHMF", MISX, FinamIntervalEnum.ONE_DAY, str(RUB)),
        ("SBER", MISX, FinamIntervalEnum.ONE_DAY, str(RUB)),
    ]
    MOEX_TICKERS: list[tuple[str, str, MOEXIntervalEnum, str]] = [
        ("IMOEX", MISX, MOEXIntervalEnum.ONE_DAY, str(RUB)),
        ("MCFTRR", MISX, MOEXIntervalEnum.ONE_DAY, str(RUB)),
    ]


@op(required_resource_keys={"settings"}, out=DynamicOut())
def finam_tickers(
    context: OpExecutionContext,
) -> Generator[DynamicOutput[tuple[str, str, FinamIntervalEnum, str]], None, None]:
    for ticker, venue, interval, currency in context.resources.settings.FINAM_TICKERS:
        mapping_key: str = f"{ticker}_{venue}_{interval}_{currency}"
        yield DynamicOutput(value=(ticker, venue, interval, currency), mapping_key=mapping_key)


@op(required_resource_keys={"services"})
async def process_finam(context: OpExecutionContext, item: tuple[str, str, FinamIntervalEnum, str]) -> DataFrame:
    ticker, venue, interval, currency = item
    latest_timestamp: datetime | None = context.resources.services["ohlcv_dwh_service"].query_latest_timestamp(
        ticker=ticker,
        interval=finam_to_messoyakha_interval(interval),
        product=MISXProductEnum.SPOT.value,
        venue=venue,
        currency=currency,
    )
    logger.info(f"Latest timestamp for {ticker}-{venue}-{interval}-{currency} is {latest_timestamp}.")

    ohlcv: DataFrame = context.resources.services["finam_dlh_service"].query_ohlcv(
        ticker=ticker,
        venue=venue,
        product=MISXProductEnum.SPOT.value,
        currency=currency,
        interval=interval,
        since_date=latest_timestamp,
    )
    ohlcv = ohlcv.with_columns(
        col("interval").replace(finam_to_messoyakha_interval_mapping(), default=col("interval")),
        month=col("timestamp").dt.month(),
        year=col("timestamp").dt.year(),
    )
    logger.info(f"Got finam OHLCV for {ticker}, shape is {ohlcv.shape}.")
    return ohlcv


@op(required_resource_keys={"settings"}, out=DynamicOut())
def moex_tickers(
    context: OpExecutionContext,
) -> Generator[DynamicOutput[tuple[str, str, MOEXIntervalEnum, str]], None, None]:
    for ticker, venue, interval, currency in context.resources.settings.MOEX_TICKERS:
        mapping_key: str = f"{ticker}_{venue}_{interval}_{currency}"
        yield DynamicOutput(value=(ticker, venue, interval, currency), mapping_key=mapping_key)


@op(required_resource_keys={"services"})
async def process_moex(context: OpExecutionContext, item: tuple[str, str, MOEXIntervalEnum, str]) -> DataFrame:
    ticker, venue, interval, currency = item
    latest_timestamp: datetime | None = context.resources.services["ohlcv_dwh_service"].query_latest_timestamp(
        ticker=ticker,
        venue=venue,
        product=MISXProductEnum.SPOT.value,
        currency=currency,
        interval=moex_iss_to_messoyakha_interval(interval),
    )
    logger.info(f"Latest timestamp for {ticker}-{venue}-{interval}-{currency} is {latest_timestamp}.")

    ohlcv: DataFrame = context.resources.services["moex_iss_dlh_service"].query_ohlcv(
        ticker=ticker,
        venue=venue,
        product=MISXProductEnum.SPOT.value,
        currency=currency,
        interval=interval,
        since_date=latest_timestamp,
    )
    ohlcv = ohlcv.with_columns(
        col("interval").replace(moex_iss_to_messoyakha_interval_mapping(), default=col("interval")),
        month=col("timestamp").dt.month(),
        year=col("timestamp").dt.year(),
    )
    logger.info(f"Got MOEX ISS OHLCV for {ticker}, shape is {ohlcv.shape}.")
    return ohlcv


@op(required_resource_keys={"services"})
def load_ohlcv(context: OpExecutionContext, finam_data: list[DataFrame], moex_iss_data: list[DataFrame]) -> None:
    ohlcv: DataFrame = concat(
        [concat(finam_data, how="diagonal_relaxed"), concat(moex_iss_data, how="diagonal_relaxed")],
        how="diagonal_relaxed",
    )
    logger.info(f"Got OHLCV to load, shape is {ohlcv.shape}.")
    if not ohlcv.is_empty():
        ohlcv = ohlcv.with_columns(
            _partition_by_ticker=col("ticker"),
            _partition_by_interval=col("interval"),
            _partition_by_product=col("product"),
            _partition_by_venue=col("venue"),
            _partition_by_currency=col("currency"),
            _partition_by_month=col("month"),
            _partition_by_year=col("year"),
        ).pipe(OHLCVSchema.validate)
        logger.info(f"OHLCV shape after validation is {ohlcv.shape}.")

        context.resources.services["ohlcv_dwh_service"].load_to_dwh(
            data=ohlcv,
            path="s3://54bb0ca3-5204-4d58-ad1b-3a731de6a032/ohlcv/",
            partitions=[
                "_partition_by_ticker",
                "_partition_by_interval",
                "_partition_by_product",
                "_partition_by_venue",
                "_partition_by_currency",
                "_partition_by_month",
                "_partition_by_year",
            ],
        )


@graph
def ohlcv() -> None:
    load_ohlcv(
        finam_data=finam_tickers().map(process_finam).collect(),
        moex_iss_data=moex_tickers().map(process_moex).collect(),
    )


class Container(BaseContainer):
    settings: Factory[_OHLCVDWHSettings] = Factory(_OHLCVDWHSettings)
    job: Singleton[JobDefinition] = Singleton(
        ohlcv.to_job,
        name=Factory(lambda: ohlcv.__name__),  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
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
                ohlcv_dwh_service=Factory(  # type: ignore[missing-argument]
                    OHLCVService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        OHLCVS3Repository,
                        options=Factory(  # type: ignore[unexpected-keyword]
                            S3StorageOptionsSchema,
                            access_key=settings.ACCESS_KEY,
                            secret_key=settings.SECRET_KEY,
                            endpoint=settings.ENDPOINT,
                            region=settings.REGION,
                        ),
                    ),
                ),
                moex_iss_dlh_service=Factory(  # type: ignore[missing-argument]
                    MOEXISSDLHService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        MOEXISSS3Repository,
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
