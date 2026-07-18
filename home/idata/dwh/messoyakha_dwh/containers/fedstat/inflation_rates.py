from datetime import datetime

from dagster import JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from polars import DataFrame, col
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_fedstat_sdk.schemas.inflation_rate import FedstatInflationRateInputSchema
from messoyakha_fedstat_sdk.services.fedstat import FedstatService
from messoyakha_moex_iss_sdk.schemas.listed_from import MOEXListedFromInputSchema
from messoyakha_moex_iss_sdk.services.moex import MOEXStockIndexService
from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema

from messoyakha_dlh.adapters.repositories.fedstat import FedStatS3Repository
from messoyakha_dlh.schemas.fedstat import FedstatInflationRateSchema
from messoyakha_dlh.services.fedstat import FedstatDLHService
from messoyakha_dlh.settings import DLHSettings


@op(required_resource_keys={"services"})
async def query_latest_inflation_rate_timestamp(context: OpExecutionContext) -> datetime:
    latest_timestamp: datetime | None = context.resources.services[
        "fedstat_dlh_service"
    ].query_latest_inflation_rate_timestamp()
    if not latest_timestamp:
        latest_timestamp = await context.resources.services["moex_iss_sdk_service"].get_first_trade_date(
            input_schema=MOEXListedFromInputSchema(ticker="IMOEX")
        )
    logger.info(f"Latest Fedstat inflation rate timestamp is {latest_timestamp}.")
    return latest_timestamp


@op(required_resource_keys={"services", "settings"})
async def get_inflation_rates(context: OpExecutionContext, latest_timestamp: datetime) -> DataFrame:
    inflation_rates: DataFrame = await context.resources.services["fedstat_sdk_service"].get_inflation_rates(
        input_schema=FedstatInflationRateInputSchema(
            start_date=latest_timestamp, end_date=context.resources.settings.TRIGGER_DATE
        )
    )
    inflation_rates = inflation_rates.filter(col("timestamp") > latest_timestamp)
    inflation_rates = inflation_rates.with_columns(
        _partition_by_year=col("timestamp").dt.year(),
        _partition_by_month=col("timestamp").dt.month(),
    )
    logger.info(f"Got inflation rates, shape is {inflation_rates.shape}.")
    return inflation_rates


@op(required_resource_keys={"settings", "services"})
def load_inflation_rates(context: OpExecutionContext, inflation_rates: DataFrame) -> None:
    logger.info(f"Got inflation rates to load, shape is {inflation_rates.shape}.")
    if not inflation_rates.is_empty():
        inflation_rates = FedstatInflationRateSchema.validate(inflation_rates)
        logger.info(f"Inflation rates shape after validation is {inflation_rates.shape}.")

        context.resources.services["fedstat_dlh_service"].load_to_dlh(
            data=inflation_rates,
            path="s3://f8e90488-f511555d-274b-4258-bffc-572dd1900382/fedstat/inflation-rates/",
            partitions=["_partition_by_year", "_partition_by_month"],
        )


@graph
def fedstat_inflation_rates() -> None:
    load_inflation_rates(inflation_rates=get_inflation_rates(latest_timestamp=query_latest_inflation_rate_timestamp()))


class Container(BaseContainer):
    settings: Factory[DLHSettings] = Factory(DLHSettings)
    job: Singleton[JobDefinition] = Singleton(
        fedstat_inflation_rates.to_job,
        name=Factory(lambda: fedstat_inflation_rates.__name__),  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                fedstat_sdk_service=Factory(FedstatService),
                moex_iss_sdk_service=Factory(MOEXStockIndexService),  # type: ignore[bad-argument-type]
                fedstat_dlh_service=Factory(  # type: ignore[missing-argument]
                    FedstatDLHService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        FedStatS3Repository,
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
