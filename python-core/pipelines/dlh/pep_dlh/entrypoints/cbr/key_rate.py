from datetime import datetime, timezone
from typing import Final

from dagster import In, JobDefinition, Nothing, OpExecutionContext, graph, op
from loguru import logger
from polars import DataFrame
from pyiceberg.partitioning import DayTransform, PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.types import DoubleType, NestedField, TimestamptzType
from that_depends import BaseContainer, Provide, inject
from that_depends.providers import Dict, Factory, Singleton

from pep_sdk.schemas.clients.cbr.key_rate import CBRKeyRateParametersSchema
from pep_sdk.services.clients.cbr import CBRService as CBRSDKService

from pep_dlh.settings import Settings


_S3_ICEBERG_DLH_CBR_KEY_RATE_TABLE: Final[str] = "{namespace}.cbr-key-rate"
_CBR_FIRST_DATE: Final[datetime] = datetime(year=2010, month=1, day=1, tzinfo=timezone.utc)


@op(required_resource_keys={"settings"})
def setup_s3_iceberg(context: OpExecutionContext) -> None:
    context.resources.settings.catalog.create_namespace_if_not_exists(namespace=context.resources.settings.NAMESPACE)
    if context.resources.settings.catalog.namespace_exists(identifier=context.resources.settings.NAMESPACE):
        context.resources.settings.catalog.create_table_if_not_exists(
            identifier=_S3_ICEBERG_DLH_CBR_KEY_RATE_TABLE.format(namespace=context.resources.settings.NAMESPACE),
            schema=Schema(
                NestedField(field_id=1, name="key_rate", field_type=DoubleType()),  # type: ignore[missing-argument]
                NestedField(field_id=2, name="timestamp", field_type=TimestamptzType()),  # type: ignore[missing-argument]
            ),
            partition_spec=PartitionSpec(
                PartitionField(source_id=2, field_id=1000, transform=DayTransform(), name="_partition_by_timestamp"),  # type: ignore[missing-argument]
            ),
        )


@op(ins={"depends_on_s3_iceberg_setup": In(Nothing)}, required_resource_keys={"services", "settings"})
def get_key_rates(context: OpExecutionContext) -> DataFrame:
    key_rates: DataFrame = context.resources.services["cbr_sdk_service"].get_key_rates(
        parameters_schema=CBRKeyRateParametersSchema(
            start_time=_CBR_FIRST_DATE, end_time=context.resources.settings.TRIGGER_DATE
        )
    )
    logger.info(f"Got key rates, shape is {key_rates.shape}.")

    return key_rates


@op(required_resource_keys={"settings"})
def load_to_s3_iceberg(context: OpExecutionContext, data: DataFrame) -> None:
    dlh_cbr_key_rate_s3_iceberg_table: str = _S3_ICEBERG_DLH_CBR_KEY_RATE_TABLE.format(
        namespace=context.resources.settings.NAMESPACE
    )
    if context.resources.settings.catalog.table_exists(identifier=dlh_cbr_key_rate_s3_iceberg_table):
        data.write_iceberg(
            target=context.resources.settings.catalog.load_table(dlh_cbr_key_rate_s3_iceberg_table),
            mode="overwrite",
        )


@graph
def cbr_key_rate_api_pipeline() -> None:
    load_to_s3_iceberg(data=get_key_rates(depends_on_s3_iceberg_setup=setup_s3_iceberg()))


class Container(BaseContainer):
    job: Singleton[JobDefinition] = Singleton(
        cbr_key_rate_api_pipeline.to_job,
        name=cbr_key_rate_api_pipeline.__name__,  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(cbr_sdk_service=Factory(CBRSDKService)),
            settings=Factory(Settings),  # type: ignore[bad-argument-type]
        ),
    )


@inject
def main(job: JobDefinition = Provide[Container.job]) -> None:
    job.execute_in_process()


if __name__ == "__main__":
    main()
