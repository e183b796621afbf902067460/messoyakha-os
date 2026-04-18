# Python Agent Standards

As an agent, always load the following skills while working on codebase in `python-core/`: `/dignified-python` and `/python-tests` skills must always be loaded into the agent context and conscientiously applied, you can find them in provided URLs in `.kilo/kilo.json`.

## Python Monorepo Structure

The `python-core/` contains a `uv` [workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/#workspace-layouts) defining multiple internal packages:

- `pep-api` in `python-core/workspaces/api`: the API clients for each external data provider;
- `pep-lakehouse` in `python-core/workspaces/lakehouse`: general lakehouse schema based on `S3` and `Apache Iceberg`.

And the core apps:

- in `python-core/pipelines` we store all general data pipelines: we use `dagster` framework as a data pipeline orchestrator;
- In `python-core/strategies` we store our core strategies and backtests pipelines: we use `backtesting` and `bt` libraries for backtests.
