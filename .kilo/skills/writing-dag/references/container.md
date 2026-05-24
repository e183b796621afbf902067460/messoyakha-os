# Container

The container is the DAG definition: Dagster ops, a `@graph`, and a `BaseContainer` subclass with resource wiring.

## Op Sequence

| Step | Op | Required |
|------|-----|----------|
| 1 | `migrate_*` | S3 DAGs only |
| 2 | `query_latest_timestamp` | Iterative only |
| 3 | `get_*` / `crawl_*` | All |
| 4 | `load_*` / `export_*` | All |

**Step 1 — migrate**: calls `settings.catalog.create_namespace_if_not_exists` then `service.migrate_*()` which chains `_v1()`, `_v2()`, etc. to create Iceberg tables.

**Step 2 — query_latest_timestamp**: runs `MAX(timestamp)` via DuckDB `iceberg_scan` on the target table; returns `CATCH_UP_DATE` when table is empty. Needs `ins={"is_migrated": In(Nothing)}` to wait for migration.

**Step 3 — fetch**: acquires data from SDK service. Receives `latest_timestamp` (for iterative) or no timestamp (for overwrite). Iterative fetches filter strictly with `col("timestamp") > latest_timestamp`.

**Step 4 — load/export**: writes DataFrame to Iceberg (`"append"` or `"overwrite"`) or exports to file. Guards empty results with `if not df.is_empty()`.

## Graph Wiring

```python
@graph
def cbr_key_rates() -> None:
    load_key_rates(key_rates=get_key_rates(
        latest_timestamp=query_latest_timestamp(is_migrated=migrate_key_rates())
    ))
```

Dynamic fan-out for parallel processing:

```python
@graph
def dohod_dividends() -> None:
    load_dividends(data=(tickers(is_migrated=migrate_dividends()).map(crawl_dividends)).collect())
```

## Container Class

Wires everything with `that-depends` providers:

```python
from that_depends import BaseContainer
from that_depends.providers import Dict, Factory, Singleton

class Container(BaseContainer):
    alias: str | None = "CBRKeyRatesContainer"

    settings: Factory[CBRKeyRatesDLHSettings] = Factory(CBRKeyRatesDLHSettings)
    job: Singleton[JobDefinition] = Singleton(
        cbr_key_rates.to_job,
        name=cbr_key_rates.__name__,
        resource_defs=Dict(
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
                            endpoint=settings.ENDPOINT,
                            region=settings.REGION,
                        ),
                    ),
                ),
            ),
            settings=settings,
        ),
        tags=Dict(source=settings.NAMESPACE),
    )
```

Key providers: `Factory` (new instance per resolution), `Singleton` (single lazy instance), `Dict` (for Dagster's `resource_defs`). The `connection` Factory passes S3 credentials from `settings.*` to the `connect()` callable from `messoyakha_s3_sdk.adapters.connections.duckdb`. For parallel crawling, add:

```python
executor_def=Factory(
    multiprocess_executor.configured, config_or_config_fn=Dict(max_concurrent=Factory(lambda: 2))
),
```

## Service Layer

Services are `attrs` `@define` classes. They delegate everything to adapters, receiving settings via `@inject`:

```python
@define(slots=True, auto_attribs=True, kw_only=True)
class CBRKeyRatesDLHService:
    _repository: CBRKeyRatesS3Repository  # resolved via container wiring

    @inject
    def load_key_rates(
        self, key_rates: DataFrame, settings: CBRKeyRatesDLHSettings = Provide["CBRKeyRatesContainer.settings"]
    ) -> None:
        self._repository.load_key_rates(key_rates=key_rates, catalog=settings.catalog, namespace=settings.NAMESPACE)
```

The `Provide[...]` string references the container's alias — always `<Alias>.settings`.

## Repository Base

S3 repositories extend `DuckDBIcebergS3RepositoryBase` from `messoyakha_coupling.adapters.repositories.s3`, which provides a `_connection: DuckDBPyConnection` and helpers `_query_pl(query) -> DataFrame` and `_query_one(query) -> Any`.

Iceberg schema versioning uses `_vN()` methods, chained in `migrate_*()`. Never modify an existing version — add a new one.

Repository structure:
- `_namespace: str` and `_table: str` fields (default values, `init=False`)
- `migrate_*()` chains `_v1()`, `_v2()` — creates namespace + table with `create_table_if_not_exists`
- `load_*()` writes DataFrame via `write_iceberg(target=catalog.load_table(...), mode="append"|"overwrite")`, guarded by `catalog.table_exists()`

Partitioning conventions: temporal columns use `DayTransform()` (field_id=1000), categorical use `IdentityTransform()`. Field IDs start at 1000, increment per field.

## Entrypoint

```python
@Container.inject
def main(job: JobDefinition = Provide[Container.job]) -> None:
    job.execute_in_process()
```

Run: `uv run home/idata/dags/dlh/.../<entrypoints>/<source>/<entity>.py`
