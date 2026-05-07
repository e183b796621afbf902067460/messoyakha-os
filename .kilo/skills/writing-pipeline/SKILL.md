---
name: writing-pipeline
description: Creates data pipeline using Dagster orchestration, that-depends DI, and Iceberg/S3 persistence. Use when adding a new entrypoint pipeline or extending existing ones with ops, graphs, tables, or services. Do not use for fixing type errors, updating settings classes, or SDK-level changes outside pipeline entrypoints.
---

# Writing Data Pipelines

This project combines three core technologies to write data pipelines (DAGs):

| Technology | Purpose |
|---|---|
| [Dagster](https://docs.dagster.io/) | Orchestration: `op`/`graph`/`job`, resource injection, execution |
| [that-depends](https://that-depends.readthedocs.io/llms.txt) | Application-level DI containers: `BaseContainer`, `Singleton`, `Factory`, `Dict`, `@inject` |
| [PyIceberg](https://py.iceberg.apache.org/) | Table schemas, partitions, S3-backed catalogs |

Two reference implementations exist:

| File | Pattern |
|---|---|
| `entrypoints/dohod/crawl_dividends.py` | Fan-out via `DynamicOut` + mocked in-memory source |
| `entrypoints/cbr/key_rate.py` | Simple sequential: setup -> fetch -> load |

Before writing a new pipeline, read both. See `references/stack.md` for deeper architectural context.

## Step 1 — Determine the Pipeline Module

Pipelines live in `python-core/pipelines/<module>/pep_<module>/entrypoints/<entrypoint>/`. Each entrypoint has:

- `__init__.py` (empty);
- A feature files (e.g., `key_rate.py`).

The settings class for the module lives at `python-core/pipelines/<module>/pep_<module>/settings.py` and extends `SettingsBase` from `pep_sdk.settings.base` which is also may be extended in a feature file as well.

## Step 2 — Define the Entrypoint File

Create the feature file under the target entrypoint directory. Follow this exact structure from top to bottom.

### 2.1 Table Name Constant

Define the Iceberg table identifier at module top-level:

```python
_S3_ICEBERG_<MODULE>_<ENTRYPOINT>_TABLE: Final[str] = "{namespace}.<kebab-table-name>"
```

The `{namespace}` placeholder is filled at runtime from `settings.NAMESPACE`.

### 2.2 Ops

Every pipeline has ops. Declare each op as a standalone function.

#### `setup_s3_iceberg`

```python
@op(required_resource_keys={"settings"})
def setup_s3_iceberg(context: OpExecutionContext) -> None:
    ...
```

Responsible for:

1. `create_namespace_if_not_exists` — idempotent namespace creation;
2. `create_table_if_not_exists` — guarded by `namespace_exists` check;
3. Defining `Schema` with `NestedField` entries ordered by `field_id`;
4. Defining `PartitionSpec` with `PartitionField` entries.

Common field types: `TimestamptzType`, `DoubleType`, `StringType`.
Common partition transforms: `DayTransform` (time-based), `IdentityTransform` (categorical).

#### `<fetch>_op`

Either a simple op or a dynamic fan-out. The simple pattern:

```python
@op(ins={"depends_on_s3_iceberg_setup": In(Nothing)}, required_resource_keys={"services", "settings"})
def get_<data>(context: OpExecutionContext) -> DataFrame:
    ...
    return df
```

- `ins={"depends_on_s3_iceberg_setup": In(Nothing)}` enforces ordering: this op runs after `setup_s3_iceberg`;
- `required_resource_keys={"services", "settings"}` injects both DI resources;
- Services are accessed via `context.resources.services["<service_key>"]`;
- Settings are accessed via `context.resources.settings.<field>`;
- Parameter schemas from SDK are passed directly to service methods.

Use `logger.info(...)` from `loguru` for progress logging.

#### `load_to_s3_iceberg`

```python
@op(required_resource_keys={"settings"})
def load_to_s3_iceberg(context: OpExecutionContext, data: DataFrame) -> None:
    ...
```

Accepts a `DataFrame` (or `list[DataFrame]` if collecting dynamic outputs). Builds the full table identifier, checks `table_exists`, then calls `data.write_iceberg(target=..., mode="overwrite")`.

### 2.3 Graph

Wire ops into a graph. The simple sequential pattern:

```python
@graph
def <module>_<entrypoint>_pipeline() -> None:
    load_to_s3_iceberg(
        data=get_<data>(depends_on_s3_iceberg_setup=setup_s3_iceberg())
    )
```

The name must follow the `<module>_<entrypoint>_pipeline` pattern.

### 2.4 Container

Encapsulate the entire pipeline runtime configuration in a `Container`:

```python
class Container(BaseContainer):
    job: Singleton[JobDefinition] = Singleton(
        <pipeline_name>.to_job,
        name=<pipeline_name>.__name__,  # type: ignore[missing-attribute]
        resource_defs=Dict(  # type: ignore[bad-argument-type]
            services=Dict(<service_key>=Factory(<ServiceClass>)),
            settings=Factory(Settings),  # type: ignore[bad-argument-type]
        ),
        executor_def=Factory(  # type: ignore[bad-argument-type]
            multiprocess_executor.configured, config_or_config_fn=Dict(max_concurrent=Factory(lambda: 2))
        ),
    )
```

Key points:

- `services` is a `Dict` mapping string keys to `Factory` instances of service classes;
- `settings` is a `Factory` wrapping the module's `Settings` class;
- `executor_def` wraps `multiprocess_executor` with a concurrency cap;
- Every line with a pyrefly false-positive needs `# type: ignore[...]` — copy the exact ignore comments from a reference implementation.

### 2.5 Main Entry Point

```python
@inject
def main(job: JobDefinition = Provide[Container.job]) -> None:
    job.execute_in_process()


if __name__ == "__main__":
    main()
```

## Step 3 — Dependencies and Imports

- If the service client is new, ensure it exists in `pep_sdk/services/` before referencing it from a pipeline;
- If the parameter schema is new, ensure it exists in `pep_sdk/schemas/` before referencing it;
- All SDK-level types (services, schemas) are imported from `pep_sdk.*`;
- All pipeline-level types (settings) are imported from `pep_<module>.*` under `pipelines/` directory.

## Error Handling

- PyIceberg type constructors (`TimestamptzType()`, `DoubleType()`, `DayTransform()`) trigger `missing-argument` from pyrefly — suppress with `# type: ignore[missing-argument]`;
- `GraphDefinition` has no `__name__` attribute at type-check level — suppress with `# type: ignore[missing-attribute]`;
- `that-depends` `Dict`/`Factory` providers trigger `bad-argument-type` against Dagster's resource definitions — suppress with `# type: ignore[bad-argument-type]`;
- Never invent new services or schemas in the pipeline file: push that logic into SDK first;
- If a required service key doesn't exist in the services `Dict`, the error is a runtime `KeyError` — ensure the service class is imported and wired in the `Container`.
