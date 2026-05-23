from dagster import In, JobDefinition, Nothing, OpExecutionContext, graph, op
from loguru import logger
from polars import DataFrame
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

from messoyakha_cbr_sdk.schemas.key_rate import CBRKeyRateParametersSchema
from messoyakha_cbr_sdk.services.cbr import CBRService
from messoyakha_s3_sdk.adapters.connections.duckdb import connect

from messoyakha_dlh.adapters.repositories.cbr.key_rates import CBRKeyRatesS3Repository
from messoyakha_dlh.services.cbr.key_rates import CBRKeyRatesDLHService, CBRKeyRatesDLHSettings


@op(required_resource_keys={"settings", "services"})
def migrate_key_rates(context: OpExecutionContext) -> None:
    context.resources.settings.catalog.create_namespace_if_not_exists(namespace=context.resources.settings.NAMESPACE)
    if context.resources.settings.catalog.namespace_exists(identifier=context.resources.settings.NAMESPACE):
        context.resources.services["cbr_dlh_service"].migrate_key_rates()


@op(ins={"is_migrated": In(Nothing)}, required_resource_keys={"services", "settings"})
def get_key_rates(context: OpExecutionContext) -> DataFrame:
    key_rates: DataFrame = context.resources.services["cbr_sdk_service"].get_key_rates(
        parameters_schema=CBRKeyRateParametersSchema(
            start_time=context.resources.settings.CATCH_UP_DATE, end_time=context.resources.settings.TRIGGER_DATE
        )
    )
    logger.info(f"Got key rates, shape is {key_rates.shape}.")
    return key_rates


@op(required_resource_keys={"settings", "services"})
def load_key_rates(context: OpExecutionContext, key_rates: DataFrame) -> None:
    logger.info(f"Got key rates to load, shape is {key_rates.shape}.")
    if not key_rates.is_empty():
        context.resources.services["cbr_dlh_service"].load_key_rates(key_rates=key_rates)


@graph
def cbr_key_rates() -> None:
    load_key_rates(key_rates=get_key_rates(is_migrated=migrate_key_rates()))


class Container(BaseContainer):
    alias: str = "CBRKeyRatesContainer"

    settings: Factory[CBRKeyRatesDLHSettings] = Factory(CBRKeyRatesDLHSettings)
    job: Singleton[JobDefinition] = Singleton(
        cbr_key_rates.to_job,
        name=cbr_key_rates.__name__,  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(
                cbr_sdk_service=Factory(CBRService),
                cbr_dlh_service=Factory(
                    CBRKeyRatesDLHService,
                    repository=Factory(
                        CBRKeyRatesS3Repository,
                        connection=Factory(
                            connect,
                            access_key=settings.ACCESS_KEY,
                            secret_key=settings.SECRET_KEY,
                            endpoint=settings.ENDPOINT.encoded_string(),
                            region=settings.REGION,
                        ),
                    ),
                ),
            ),
            settings=settings,  # type: ignore[bad-argument-type]
        ),
        tags=Dict(source=settings.NAMESPACE),
    )
