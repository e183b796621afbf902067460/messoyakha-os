from collections.abc import Generator

from dagster import DynamicOut, DynamicOutput, JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from nautilus_trader.model.currencies import RUB
from polars import DataFrame, concat
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_sdk.adapters.venues.misx import MISX
from messoyakha_sdk.enums.intervals import MessoyakhaIntervalEnum
from messoyakha_sdk.enums.venues.misx import MISXProductEnum
from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema

from messoyakha_northern_weather.adapters.ohlcv import OHLCVS3Repository
from messoyakha_northern_weather.services.ohlcv import OHLCVService
from messoyakha_northern_weather.settings import NorthernWeatherSettings


class _OHLCVSettings(NorthernWeatherSettings):
    TICKERS: list[tuple[str, str, MessoyakhaIntervalEnum, str]] = [
        ("SIBN", MISX, MessoyakhaIntervalEnum.ONE_DAY, str(RUB)),
        ("NVTK", MISX, MessoyakhaIntervalEnum.ONE_DAY, str(RUB)),
        ("TRNFP", MISX, MessoyakhaIntervalEnum.ONE_DAY, str(RUB)),
        ("PHOR", MISX, MessoyakhaIntervalEnum.ONE_DAY, str(RUB)),
        ("PLZL", MISX, MessoyakhaIntervalEnum.ONE_DAY, str(RUB)),
        ("GMKN", MISX, MessoyakhaIntervalEnum.ONE_DAY, str(RUB)),
        ("CHMF", MISX, MessoyakhaIntervalEnum.ONE_DAY, str(RUB)),
        ("SBER", MISX, MessoyakhaIntervalEnum.ONE_DAY, str(RUB)),
        ("MCFTRR", MISX, MessoyakhaIntervalEnum.ONE_DAY, str(RUB)),
    ]


@op(required_resource_keys={"settings"}, out=DynamicOut())
def tickers(
    context: OpExecutionContext,
) -> Generator[DynamicOutput[tuple[str, str, MessoyakhaIntervalEnum, str]], None, None]:
    for ticker, venue, interval, currency in context.resources.settings.TICKERS:
        mapping_key: str = f"{ticker}_{venue}_{interval}_{currency}"
        yield DynamicOutput(value=(ticker, venue, interval, currency), mapping_key=mapping_key)


@op(required_resource_keys={"services"})
def query_ohlcv(context: OpExecutionContext, item: tuple[str, str, MessoyakhaIntervalEnum, str]) -> DataFrame:
    ticker, venue, interval, currency = item
    ohlcv: DataFrame = context.resources.services["ohlcv_dwh_service"].query_ohlcv(
        ticker=ticker,
        venue=venue,
        product=MISXProductEnum.SPOT.value,
        currency=currency,
        interval=interval,
    )
    logger.info(f"Got OHLCV for {ticker}-{venue}-{interval}-{currency}, shape is {ohlcv.shape}.")
    return ohlcv


@op
def load(data: list[DataFrame]) -> None:
    ohlcv: DataFrame = concat(data)
    logger.info(f"Got all OHLCV, shape is {ohlcv.shape}.")

    ohlcv.write_parquet("ohlcv.parquet")


@graph
def ohlcv() -> None:
    load(data=tickers().map(query_ohlcv).collect())


class Container(BaseContainer):
    settings: Factory[_OHLCVSettings] = Factory(_OHLCVSettings)
    job: Singleton[JobDefinition] = Singleton(
        ohlcv.to_job,
        name=Factory(lambda: ohlcv.__name__),  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
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
            ),
            settings=settings,  # type: ignore[bad-argument-type]
        ),
    )
