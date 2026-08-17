from collections.abc import Generator

from dagster import DynamicOut, DynamicOutput, JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from nautilus_trader.model.currencies import RUB
from polars import DataFrame, concat
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_sdk.adapters.venues.misx import MISX
from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema

from messoyakha_northern_weather.adapters.dividends import DividendsS3Repository
from messoyakha_northern_weather.services.dividends import DividendsService
from messoyakha_northern_weather.settings import NorthernWeatherSettings


class _DividendsSettings(NorthernWeatherSettings):
    TICKERS: list[tuple[str, str, str]] = [
        ("SIBN", MISX, str(RUB)),
        ("NVTK", MISX, str(RUB)),
        ("TRNFP", MISX, str(RUB)),
        ("PHOR", MISX, str(RUB)),
        ("PLZL", MISX, str(RUB)),
        ("GMKN", MISX, str(RUB)),
    ]


@op(required_resource_keys={"settings"}, out=DynamicOut())
def tickers(context: OpExecutionContext) -> Generator[DynamicOutput[tuple[str, str, str]], None, None]:
    for ticker, venue, currency in context.resources.settings.TICKERS:
        mapping_key: str = f"{ticker}_{venue}_{currency}"
        yield DynamicOutput(value=(ticker, venue, currency), mapping_key=mapping_key)


@op(required_resource_keys={"services"})
def query_dividends(context: OpExecutionContext, item: tuple[str, str, str]) -> DataFrame:
    ticker, venue, currency = item
    dividends: DataFrame = context.resources.services["dividends_dwh_service"].query_dividends(
        ticker=ticker, venue=venue, currency=currency
    )
    logger.info(f"Got dividends for {ticker}-{venue}-{currency}, shape is {dividends.shape}.")
    return dividends


@op
def load(data: list[DataFrame]) -> None:
    dividends: DataFrame = concat(data)
    logger.info(f"Got all dividends, shape is {dividends.shape}.")

    dividends.write_parquet("dividends.parquet")


@graph
def dividends() -> None:
    load(data=tickers().map(query_dividends).collect())


class Container(BaseContainer):
    settings: Factory[_DividendsSettings] = Factory(_DividendsSettings)
    job: Singleton[JobDefinition] = Singleton(
        dividends.to_job,
        name=Factory(lambda: dividends.__name__),  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
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
