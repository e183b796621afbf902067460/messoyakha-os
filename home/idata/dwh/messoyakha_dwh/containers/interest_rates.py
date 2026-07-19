from datetime import datetime

from dagster import JobDefinition, OpExecutionContext, graph, op
from loguru import logger
from polars import DataFrame, col, concat
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_sdk.adapters.banks.cbr import CBR
from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema

from messoyakha_dlh.adapters.repositories.cbr import CBRS3Repository
from messoyakha_dlh.services.cbr import CBRDLHService
from messoyakha_dwh.adapters.repositories.interest_rates import InterestRatesS3Repository
from messoyakha_dwh.schemas.interest_rates import InterestRatesSchema
from messoyakha_dwh.services.interest_rates import InterestRatesService
from messoyakha_dwh.settings import DWHSettings


@op(required_resource_keys={"services"})
async def process_cbr(context: OpExecutionContext) -> DataFrame:
    latest_timestamp: datetime | None = context.resources.services[
        "interest_rates_dwh_service"
    ].query_bank_latest_timestamp(bank=CBR)
    interest_rates: DataFrame = context.resources.services["cbr_dlh_service"].query_interest_rates(
        since_date=latest_timestamp
    )
    return interest_rates.with_columns(
        month=col("timestamp").dt.month(),
        year=col("timestamp").dt.year(),
    )


@op(required_resource_keys={"services"})
def load_interest_rates(context: OpExecutionContext, data: list[DataFrame]) -> None:
    interest_rates: DataFrame = concat(data)
    logger.info(f"Got interest rates to load, shape is {interest_rates.shape}.")

    if not interest_rates.is_empty():
        interest_rates = interest_rates.with_columns(
            _partition_by_bank=col("bank"),
            _partition_by_month=col("month"),
            _partition_by_year=col("year"),
        )
        interest_rates = InterestRatesSchema.validate(interest_rates)
        logger.info(f"Interest rates shape after validation is {interest_rates.shape}.")

        context.resources.services["interest_rates_dwh_service"].load_to_dwh(
            data=interest_rates,
            path="s3://54bb0ca3-5204-4d58-ad1b-3a731de6a032/interest-rates/",
            partitions=["_partition_by_bank", "_partition_by_year", "_partition_by_month"],
        )


@graph
def interest_rates() -> None:
    load_interest_rates(
        data=[
            process_cbr(),
        ]
    )


class Container(BaseContainer):
    settings: Factory[DWHSettings] = Factory(DWHSettings)
    job: Singleton[JobDefinition] = Singleton(
        interest_rates.to_job,
        name=Factory(lambda: interest_rates.__name__),  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                cbr_dlh_service=Factory(  # type: ignore[missing-argument]
                    CBRDLHService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        CBRS3Repository,
                        options=Factory(  # type: ignore[unexpected-keyword]
                            S3StorageOptionsSchema,
                            access_key=settings.DLH.ACCESS_KEY,
                            secret_key=settings.DLH.SECRET_KEY,
                            endpoint=settings.DLH.ENDPOINT,
                            region=settings.DLH.REGION,
                        ),
                    ),
                ),
                interest_rates_dwh_service=Factory(  # type: ignore[missing-argument]
                    InterestRatesService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        InterestRatesS3Repository,
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
        ),
    )
