from datetime import datetime

from dagster import JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from polars import DataFrame, col
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_cbr_sdk.schemas.key_rate import CBRInterestRateInputSchema
from messoyakha_cbr_sdk.services.cbr import CBRService
from messoyakha_moex_iss_sdk.schemas.listed_from import MOEXListedFromInputSchema
from messoyakha_moex_iss_sdk.services.moex import MOEXStockIndexService
from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema

from messoyakha_dlh.adapters.repositories.cbr import CBRS3Repository
from messoyakha_dlh.schemas.cbr import CBRInterestRateSchema
from messoyakha_dlh.services.cbr import CBRDLHService
from messoyakha_dlh.settings import DLHSettings


@op(required_resource_keys={"services"})
async def query_latest_interest_rate_timestamp(context: OpExecutionContext) -> datetime:
    latest_timestamp: datetime | None = context.resources.services[
        "cbr_dlh_service"
    ].query_latest_interest_rates_timestamp()
    if not latest_timestamp:
        latest_timestamp = await context.resources.services["moex_iss_sdk_service"].get_first_trade_date(
            input_schema=MOEXListedFromInputSchema(ticker="IMOEX")
        )
    logger.info(f"Latest CBR interest rate timestamp is {latest_timestamp}.")
    return latest_timestamp


@op(required_resource_keys={"services", "settings"})
def get_interest_rates(context: OpExecutionContext, latest_timestamp: datetime) -> DataFrame:
    interest_rates: DataFrame = context.resources.services["cbr_sdk_service"].get_interest_rates(
        input_schema=CBRInterestRateInputSchema(
            start_time=latest_timestamp, end_time=context.resources.settings.TRIGGER_DATE
        )
    )
    interest_rates = interest_rates.filter(col("timestamp") > latest_timestamp)
    interest_rates = interest_rates.with_columns(
        year=col("timestamp").dt.year(),
        month=col("timestamp").dt.month(),
    )
    logger.info(f"Got interest rates, shape is {interest_rates.shape}.")
    return interest_rates


@op(required_resource_keys={"settings", "services"})
def load_interest_rates(context: OpExecutionContext, interest_rates: DataFrame) -> None:
    logger.info(f"Got interest rates to load, shape is {interest_rates.shape}.")
    if not interest_rates.is_empty():
        interest_rates = interest_rates.with_columns(
            _partition_by_year=col("year"),
            _partition_by_month=col("month"),
        ).pipe(CBRInterestRateSchema.validate)
        logger.info(f"Interest rates shape after validation is {interest_rates.shape}.")

        context.resources.services["cbr_dlh_service"].load_to_dlh(
            data=interest_rates,
            path="s3://f8e90488-f511555d-274b-4258-bffc-572dd1900382/cbr/interest-rates/",
            partitions=["_partition_by_year", "_partition_by_month"],
        )


@graph
def cbr_interest_rates() -> None:
    load_interest_rates(interest_rates=get_interest_rates(latest_timestamp=query_latest_interest_rate_timestamp()))


class Container(BaseContainer):
    settings: Factory[DLHSettings] = Factory(DLHSettings)
    job: Singleton[JobDefinition] = Singleton(
        cbr_interest_rates.to_job,
        name=Factory(lambda: cbr_interest_rates.__name__),  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                cbr_sdk_service=Factory(CBRService),
                moex_iss_sdk_service=Factory(MOEXStockIndexService),  # type: ignore[bad-argument-type]
                cbr_dlh_service=Factory(  # type: ignore[missing-argument]
                    CBRDLHService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        CBRS3Repository,
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
