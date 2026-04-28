# Python Agent Standards

A file for guiding coding agents at `/python-core`.

## Python Monorepo Structure

The `python-core/` contains a `uv` [workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/#workspace-layouts) defining multiple internal packages:

- `pep-api` in `python-core/workspaces/api`: the API clients for each external data provider;
- `pep-lakehouse` in `python-core/workspaces/lakehouse`: general lakehouse schema based on `S3` and `Apache Iceberg`.

And the core apps:

- in `python-core/pipelines` we store all general data pipelines: we use `dagster` framework as a data pipeline orchestrator;
- In `python-core/strategies` we store our core strategies and backtests pipelines.
