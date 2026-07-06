from datetime import datetime

from dagster import In, JobDefinition, Nothing, OpExecutionContext, graph, op
from loguru import logger
from polars import DataFrame, col
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_fedstat_sdk.schemas.inflation_rate import FedstatInflationRateInputSchema
from messoyakha_fedstat_sdk.services.fedstat import FedstatService
from messoyakha_sdk.adapters.connections.s3 import options

from messoyakha_dlh.adapters.repositories.fedstat.inflation_rates import FedstatInflationRatesS3Repository
from messoyakha_dlh.services.fedstat.inflation_rates import (
    FedstatInflationRatesDLHService,
    FedstatInflationRatesDLHSettings,
)


@op(required_resource_keys={"settings", "services"})
def migrate_inflation_rates(context: OpExecutionContext) -> None:
    context.resources.settings.catalog.create_namespace_if_not_exists(namespace=context.resources.settings.NAMESPACE)
    if context.resources.settings.catalog.namespace_exists(identifier=context.resources.settings.NAMESPACE):
        context.resources.services["fedstat_dlh_service"].migrate_inflation_rates()


@op(ins={"is_migrated": In(Nothing)}, required_resource_keys={"services"})
def query_latest_timestamp(context: OpExecutionContext) -> datetime:
    latest_timestamp: datetime = context.resources.services["fedstat_dlh_service"].query_latest_timestamp()
    logger.info(f"Latest Fedstat inflation rates timestamp is {latest_timestamp}.")
    return latest_timestamp


@op(required_resource_keys={"services", "settings"})
async def get_inflation_rates(context: OpExecutionContext, latest_timestamp: datetime) -> DataFrame:
    inflation_rates: DataFrame = await context.resources.services["fedstat_sdk_service"].get_inflation_rate(
        input_schema=FedstatInflationRateInputSchema(
            start_date=latest_timestamp, end_date=context.resources.settings.TRIGGER_DATE
        )
    )
    inflation_rates = inflation_rates.filter(col("timestamp") > latest_timestamp)
    logger.info(f"Got inflation rates, shape is {inflation_rates.shape}.")
    return inflation_rates


@op(required_resource_keys={"settings", "services"})
def load_inflation_rates(context: OpExecutionContext, inflation_rates: DataFrame) -> None:
    logger.info(f"Got inflation rates to load, shape is {inflation_rates.shape}.")
    if not inflation_rates.is_empty():
        context.resources.services["fedstat_dlh_service"].load_inflation_rates(inflation_rates=inflation_rates)


@graph
def fedstat_inflation_rates() -> None:
    load_inflation_rates(
        inflation_rates=get_inflation_rates(
            latest_timestamp=query_latest_timestamp(is_migrated=migrate_inflation_rates())
        )
    )


class Container(BaseContainer):
    alias: str | None = "FedstatInflationRatesContainer"

    settings: Factory[FedstatInflationRatesDLHSettings] = Factory(FedstatInflationRatesDLHSettings)
    job: Singleton[JobDefinition] = Singleton(
        fedstat_inflation_rates.to_job,
        name=fedstat_inflation_rates.__name__,  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                fedstat_sdk_service=Factory(FedstatService),
                fedstat_dlh_service=Factory(  # type: ignore[missing-argument]
                    FedstatInflationRatesDLHService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        FedstatInflationRatesS3Repository,
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
        tags=Dict(source=settings.NAMESPACE),  # type: ignore[bad-argument-type]
    )
