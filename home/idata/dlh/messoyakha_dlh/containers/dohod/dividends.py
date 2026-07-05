from collections.abc import Generator

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
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_dohod_sdk.schemas.dividends import DohodDividendsInputSchema
from messoyakha_dohod_sdk.services.dohod import DohodService
from messoyakha_s3_sdk.adapters.connections.polars import options

from messoyakha_dlh.adapters.repositories.dohod.dividends import DohodDividendsS3Repository
from messoyakha_dlh.services.dohod.dividends import DohodDividendsDLHService, DohodDividendsDLHSettings


@op(required_resource_keys={"settings", "services"})
def migrate_dividends(context: OpExecutionContext) -> None:
    context.resources.settings.catalog.create_namespace_if_not_exists(namespace=context.resources.settings.NAMESPACE)
    if context.resources.settings.catalog.namespace_exists(identifier=context.resources.settings.NAMESPACE):
        context.resources.services["dohod_dlh_service"].migrate_dividends()


@op(ins={"is_migrated": In(Nothing)}, required_resource_keys={"settings"}, out=DynamicOut())
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
        context.resources.services["dohod_dlh_service"].load_dividends(dividends=dividends)


@graph
def dohod_dividends() -> None:
    load_dividends(data=(tickers(is_migrated=migrate_dividends()).map(crawl_dividends)).collect())


class Container(BaseContainer):
    alias: str | None = "DohodDividendsContainer"

    settings: Factory[DohodDividendsDLHSettings] = Factory(DohodDividendsDLHSettings)
    job: Singleton[JobDefinition] = Singleton(
        dohod_dividends.to_job,
        name=dohod_dividends.__name__,  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                dohod_sdk_service=Factory(DohodService),
                dohod_dlh_service=Factory(  # type: ignore[missing-argument]
                    DohodDividendsDLHService,  # type: ignore[bad-argument-type]
                    repository=Factory(  # type: ignore[missing-argument, unexpected-keyword]
                        DohodDividendsS3Repository,
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
        executor_def=Factory(  # type: ignore[bad-argument-type]
            multiprocess_executor.configured, config_or_config_fn=Dict(max_concurrent=Factory(lambda: 2))
        ),
        tags=Dict(source=settings.NAMESPACE),  # type: ignore[bad-argument-type]
    )
