from collections.abc import Generator
from typing import Final

from dagster import (
    DynamicOut,
    DynamicOutput,
    In,
    JobDefinition,
    Nothing,
    OpExecutionContext,
    graph,
    multiprocess_executor,
    op,
)
from loguru import logger
from polars import DataFrame, concat
from pyiceberg.partitioning import DayTransform, IdentityTransform, PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.types import DoubleType, NestedField, StringType, TimestamptzType
from that_depends import BaseContainer, Provide, inject
from that_depends.providers import Dict, Factory, Singleton

from pep_sdk.schemas.crawlers.dohod.dividends import DohodDividendsInputSchema as DohodSDKDividendsInputSchema
from pep_sdk.services.crawlers.dohod import DohodService as DohodSDKService

from pep_dlh.settings import Settings


_DLH_DOHOD_DIVIDENDS_S3_ICEBERG_TABLE: Final[str] = "{namespace}.dohod-dividends"


@op(required_resource_keys={"settings"})
def setup_s3_iceberg(context: OpExecutionContext) -> None:
    context.resources.settings.catalog.create_namespace_if_not_exists(namespace=context.resources.settings.NAMESPACE)
    if context.resources.settings.catalog.namespace_exists(identifier=context.resources.settings.NAMESPACE):
        context.resources.settings.catalog.create_table_if_not_exists(
            identifier=_DLH_DOHOD_DIVIDENDS_S3_ICEBERG_TABLE.format(namespace=context.resources.settings.NAMESPACE),
            schema=Schema(
                NestedField(field_id=1, name="ticker", field_type=StringType()),  # type: ignore[missing-argument]
                NestedField(field_id=2, name="dividend", field_type=DoubleType()),  # type: ignore[missing-argument]
                NestedField(field_id=3, name="timestamp", field_type=TimestamptzType()),  # type: ignore[missing-argument]
            ),
            partition_spec=PartitionSpec(
                PartitionField(source_id=1, field_id=1000, transform=IdentityTransform(), name="_partition_by_ticker"),
                PartitionField(source_id=3, field_id=1001, transform=DayTransform(), name="_partition_by_timestamp"),  # type: ignore[missing-argument]
            ),
        )


@op(ins={"depends_on_s3_iceberg_setup": In(Nothing)}, out=DynamicOut())
def retrieve_mocked_tickers() -> Generator[DynamicOutput[str], None, None]:
    tickers: list[str] = [
        "SIBN",
        "ROSN",
        "TRNFP",
        "PHOR",
        "PLZL",
        "SBER",
    ]  # HOLD: RTKM (!), CHMF (!), GMKN (!), MDMG (?)
    for ticker in tickers:
        yield DynamicOutput(value=ticker, mapping_key=ticker)


@op(required_resource_keys={"services"})
async def crawl_dividends(context: OpExecutionContext, ticker: str) -> DataFrame:
    dividends: DataFrame = await context.resources.services["dohod_sdk_service"].crawl_dividends(
        input_schema=DohodSDKDividendsInputSchema(ticker=ticker)
    )
    logger.info(f"Got {ticker} dividends, shape is {dividends.shape}.")

    return dividends


@op(required_resource_keys={"settings"})
def load_to_s3_iceberg(context: OpExecutionContext, data: list[DataFrame]) -> None:
    dividends: DataFrame = concat(data)

    dlh_dohod_dividends_s3_uceberg_table: str = _DLH_DOHOD_DIVIDENDS_S3_ICEBERG_TABLE.format(
        namespace=context.resources.settings.NAMESPACE
    )
    if context.resources.settings.catalog.table_exists(identifier=dlh_dohod_dividends_s3_uceberg_table):
        dividends.write_iceberg(
            target=context.resources.settings.catalog.load_table(dlh_dohod_dividends_s3_uceberg_table),
            mode="overwrite",
        )


@graph
def dohod_dividends_crawling_pipeline() -> None:
    load_to_s3_iceberg(
        data=(retrieve_mocked_tickers(depends_on_s3_iceberg_setup=setup_s3_iceberg()).map(crawl_dividends)).collect()
    )


class Container(BaseContainer):
    job: Singleton[JobDefinition] = Singleton(
        dohod_dividends_crawling_pipeline.to_job,
        name=dohod_dividends_crawling_pipeline.__name__,  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(dohod_sdk_service=Factory(DohodSDKService)),
            settings=Factory(Settings),  # type: ignore[bad-argument-type]
        ),
        executor_def=Factory(  # type: ignore[bad-argument-type]
            multiprocess_executor.configured, config_or_config_fn=Dict(max_concurrent=Factory(lambda: 2))
        ),
    )


@inject
def main(job: JobDefinition = Provide[Container.job]) -> None:
    job.execute_in_process()


if __name__ == "__main__":
    main()
