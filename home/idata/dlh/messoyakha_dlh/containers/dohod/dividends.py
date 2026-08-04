from collections.abc import Generator

from dagster import DynamicOut, DynamicOutput, JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from polars import DataFrame, col, concat
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_dohod_sdk.schemas.dividends import DohodDividendsInputSchema
from messoyakha_dohod_sdk.services.dohod import DohodService
from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema

from messoyakha_dlh.adapters.repositories.dohod import DohodS3Repository
from messoyakha_dlh.schemas.dohod import DohodDividendsSchema
from messoyakha_dlh.services.dohod import DohodDLHService
from messoyakha_dlh.settings import DLHSettings


class _DohodDividendsDLHSettings(DLHSettings):
    TICKERS: list[str] = [
        "SIBN",
        "NVTK",
        "TRNFP",
        "PHOR",
        "PLZL",
        "SBER",
    ]


@op(required_resource_keys={"settings"}, out=DynamicOut())
def tickers(context: OpExecutionContext) -> Generator[DynamicOutput[str], None, None]:
    for ticker in context.resources.settings.TICKERS:
        yield DynamicOutput(value=ticker, mapping_key=ticker)


@op(required_resource_keys={"services"})
async def crawl_dividends(context: OpExecutionContext, ticker: str) -> DataFrame:
    dividends: DataFrame = await context.resources.services["dohod_sdk_service"].crawl_dividends(
        input_schema=DohodDividendsInputSchema(ticker=ticker)
    )
    logger.info(f"Got {ticker} dividends, shape is {dividends.shape}.")
    return dividends


@op(required_resource_keys={"settings", "services"})
def load_dividends(context: OpExecutionContext, data: list[DataFrame]) -> None:
    dividends: DataFrame = concat(data)
    logger.info(f"Got all dividends to load, shape is {dividends.shape}.")
    if not dividends.is_empty():
        dividends = dividends.with_columns(
            _partition_by_ticker=col("ticker"),
            _partition_by_venue=col("venue"),
            _partition_by_currency=col("currency"),
            _partition_by_month=col("timestamp").dt.month(),
            _partition_by_year=col("timestamp").dt.year(),
        ).pipe(DohodDividendsSchema.validate)
        logger.info(f"Dividends shape after validation is {dividends.shape}.")

        context.resources.services["dohod_dlh_service"].truncate_dlh(
            path="f8e90488-f511555d-274b-4258-bffc-572dd1900382/dohod/dividends",
        )
        context.resources.services["dohod_dlh_service"].load_to_dlh(
            data=dividends,
            path="s3://f8e90488-f511555d-274b-4258-bffc-572dd1900382/dohod/dividends/",
            partitions=[
                "_partition_by_ticker",
                "_partition_by_venue",
                "_partition_by_currency",
                "_partition_by_month",
                "_partition_by_year",
            ],
        )


@graph
def dohod_dividends() -> None:
    load_dividends(data=tickers().map(crawl_dividends).collect())


class Container(BaseContainer):
    settings: Factory[_DohodDividendsDLHSettings] = Factory(_DohodDividendsDLHSettings)
    job: Singleton[JobDefinition] = Singleton(
        dohod_dividends.to_job,
        name=Factory(lambda: dohod_dividends.__name__),  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                dohod_sdk_service=Factory(DohodService),
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
            ),
            settings=settings,  # type: ignore[bad-argument-type]
        ),
    )
