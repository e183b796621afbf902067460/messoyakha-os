from collections.abc import Generator
from datetime import datetime

from dagster import DynamicOut, DynamicOutput, JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from nautilus_trader.model.currencies import RUB
from polars import DataFrame, col, concat
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_moex_iss_sdk.schemas.history_security_total import MOEXHistorySecurityTotalInputSchema
from messoyakha_moex_iss_sdk.schemas.listed_from import MOEXListedFromInputSchema
from messoyakha_moex_iss_sdk.services.moex import MOEXStockSharesService
from messoyakha_sdk.adapters.venues.misx import MISX
from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema

from messoyakha_dlh.adapters.repositories.moex_iss import MOEXISSS3Repository
from messoyakha_dlh.schemas.moex_iss import MOEXISSTotalSupplySchema
from messoyakha_dlh.services.moex_iss import MOEXISSDLHService
from messoyakha_dlh.settings import DLHSettings


class _MOEXISSTotalSupplyDLHSettings(DLHSettings):
    TICKERS: list[tuple[str, str]] = [
        ("SIBN", str(RUB)),
        ("NVTK", str(RUB)),
        ("TRNFP", str(RUB)),
        ("PHOR", str(RUB)),
        ("PLZL", str(RUB)),
        ("GMKN", str(RUB)),
        ("SBER", str(RUB)),
    ]


@op(required_resource_keys={"settings"}, out=DynamicOut())
def tickers(
    context: OpExecutionContext,
) -> Generator[DynamicOutput[tuple[str, str]], None, None]:
    for ticker, currency in context.resources.settings.TICKERS:
        yield DynamicOutput(value=(ticker, currency), mapping_key=f"{ticker}_{currency}")


@op(required_resource_keys={"services"})
async def query_latest_total_supply_timestamp(context: OpExecutionContext, item: tuple[str, str]) -> datetime:
    ticker, currency = item
    latest_timestamp: datetime | None = context.resources.services[
        "moex_iss_dlh_service"
    ].query_latest_total_supply_timestamp(
        ticker=ticker,
        venue=MISX,
        currency=currency,
    )
    if not latest_timestamp:
        logger.info(f"Got no latest timestamp for {ticker}-{currency}, querying first trade date.")
        latest_timestamp = await context.resources.services["moex_iss_sdk_service"].get_first_trade_date(
            input_schema=MOEXListedFromInputSchema(ticker=ticker)
        )
    logger.info(f"Latest {ticker}-{currency} timestamp is {latest_timestamp}.")
    return latest_timestamp


@op(required_resource_keys={"services", "settings"})
async def get_total_supply(context: OpExecutionContext, item: tuple[str, str], latest_timestamp: datetime) -> DataFrame:
    ticker, currency = item
    total_supply: DataFrame = await context.resources.services["moex_iss_sdk_service"].get_total_supply(
        input_schema=MOEXHistorySecurityTotalInputSchema(
            ticker=ticker,
            currency=currency,
            start_time=latest_timestamp,
            end_time=context.resources.settings.TRIGGER_DATE,
        )
    )
    total_supply = total_supply.filter(col("timestamp") > latest_timestamp)
    total_supply = total_supply.with_columns(
        year=col("timestamp").dt.year(),
        month=col("timestamp").dt.month(),
    )
    min_: datetime = total_supply.select(col("timestamp").min()).item()
    max_: datetime = total_supply.select(col("timestamp").max()).item()
    logger.info(f"Got {ticker}-{currency} total supply ({min_} to {max_}), shape is {total_supply.shape}.")
    return total_supply


@op(required_resource_keys={"settings", "services"})
def load_total_supply(context: OpExecutionContext, data: list[DataFrame]) -> None:
    total_supply: DataFrame = concat(data, how="diagonal_relaxed")
    logger.info(f"Got all total supply to load, shape is {total_supply.shape}.")
    if not total_supply.is_empty():
        total_supply = total_supply.with_columns(
            _partition_by_ticker=col("ticker"),
            _partition_by_venue=col("venue"),
            _partition_by_currency=col("currency"),
            _partition_by_year=col("year"),
            _partition_by_month=col("month"),
        ).pipe(MOEXISSTotalSupplySchema.validate)
        logger.info(f"Total supply shape is {total_supply.shape}.")

        context.resources.services["moex_iss_dlh_service"].load_to_dlh(
            data=total_supply,
            path="s3://f8e90488-f511555d-274b-4258-bffc-572dd1900382/moex-iss/total-supply/",
            partitions=[
                "_partition_by_ticker",
                "_partition_by_venue",
                "_partition_by_currency",
                "_partition_by_year",
                "_partition_by_month",
            ],
        )


@graph
def process_ticker(item: tuple[str, str]) -> DataFrame:
    return get_total_supply(item=item, latest_timestamp=query_latest_total_supply_timestamp(item=item))


@graph
def moex_iss_total_supply() -> None:
    load_total_supply(data=tickers().map(process_ticker).collect())


class Container(BaseContainer):
    settings: Factory[_MOEXISSTotalSupplyDLHSettings] = Factory(_MOEXISSTotalSupplyDLHSettings)
    job: Singleton[JobDefinition] = Singleton(
        moex_iss_total_supply.to_job,
        name=Factory(lambda: moex_iss_total_supply.__name__),  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                moex_iss_sdk_service=Factory(MOEXStockSharesService),  # type: ignore[bad-argument-type]
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
