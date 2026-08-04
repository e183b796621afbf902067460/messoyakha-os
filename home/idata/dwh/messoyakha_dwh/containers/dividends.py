from collections.abc import Generator
from datetime import datetime

from dagster import DynamicOut, DynamicOutput, JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from nautilus_trader.model.currencies import RUB
from polars import DataFrame, col, concat
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_sdk.adapters.venues.misx import MISX
from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema

from messoyakha_dlh.adapters.repositories.dohod import DohodS3Repository
from messoyakha_dlh.services.dohod import DohodDLHService
from messoyakha_dwh.adapters.repositories.dividends import DividendsS3Repository
from messoyakha_dwh.schemas.dividends import DividendsSchema
from messoyakha_dwh.services.dividends import DividendsService
from messoyakha_dwh.settings import DWHSettings


class _DividendsDWHSettings(DWHSettings):
    TICKERS: list[tuple[str, str, str]] = [
        ("SIBN", MISX, str(RUB)),
        ("NVTK", MISX, str(RUB)),
        ("TRNFP", MISX, str(RUB)),
        ("PHOR", MISX, str(RUB)),
        ("PLZL", MISX, str(RUB)),
        ("SBER", MISX, str(RUB)),
    ]


@op(required_resource_keys={"settings"}, out=DynamicOut())
def tickers(context: OpExecutionContext) -> Generator[DynamicOutput[tuple[str, str, str]], None, None]:
    for ticker, venue, currency in context.resources.settings.TICKERS:
        mapping_key: str = f"{ticker}_{venue}_{currency}"
        yield DynamicOutput(value=(ticker, venue, currency), mapping_key=mapping_key)


@op(required_resource_keys={"services"})
async def process_dohod(context: OpExecutionContext, item: tuple[str, str, str]) -> DataFrame:
    ticker, venue, currency = item
    latest_timestamp: datetime | None = context.resources.services["dividends_dwh_service"].query_latest_timestamp(
        ticker=ticker, venue=venue, currency=currency
    )
    logger.info(f"Latest timestamp for {ticker}-{venue}-{currency} is {latest_timestamp}.")

    dividends: DataFrame = context.resources.services["dohod_dlh_service"].query_dividends(
        ticker=ticker, venue=venue, currency=currency, since_date=latest_timestamp
    )
    dividends = dividends.with_columns(
        month=col("timestamp").dt.month(),
        year=col("timestamp").dt.year(),
    )
    logger.info(f"Got dohod dividends for {ticker}, shape is {dividends.shape}.")
    return dividends


@op(required_resource_keys={"services"})
def load_dividends(context: OpExecutionContext, data: list[DataFrame]) -> None:
    dividends: DataFrame = concat(data)
    logger.info(f"Got dividends to load, shape is {dividends.shape}.")
    if not dividends.is_empty():
        dividends = dividends.with_columns(
            _partition_by_ticker=col("ticker"),
            _partition_by_venue=col("venue"),
            _partition_by_currency=col("currency"),
            _partition_by_month=col("month"),
            _partition_by_year=col("year"),
        ).pipe(DividendsSchema.validate)
        logger.info(f"Dividends shape after validation is {dividends.shape}.")

        context.resources.services["dividends_dwh_service"].load_to_dwh(
            data=dividends,
            path="s3://54bb0ca3-5204-4d58-ad1b-3a731de6a032/dividends/",
            partitions=[
                "_partition_by_ticker",
                "_partition_by_venue",
                "_partition_by_currency",
                "_partition_by_month",
                "_partition_by_year",
            ],
        )


@graph
def dividends() -> None:
    load_dividends(data=tickers().map(process_dohod).collect())


class Container(BaseContainer):
    settings: Factory[_DividendsDWHSettings] = Factory(_DividendsDWHSettings)
    job: Singleton[JobDefinition] = Singleton(
        dividends.to_job,
        name=Factory(lambda: dividends.__name__),  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                dohod_dlh_service=Factory(  # type: ignore[missing-argument]
                    DohodDLHService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        DohodS3Repository,
                        options=Factory(  # type: ignore[unexpected-keyword]
                            S3StorageOptionsSchema,
                            access_key=settings.ACCESS_KEY,
                            secret_key=settings.SECRET_KEY,
                            endpoint=settings.ENDPOINT,
                            region=settings.REGION,
                        ),
                    ),
                ),
                dividends_dwh_service=Factory(  # type: ignore[missing-argument]
                    DividendsService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        DividendsS3Repository,
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
