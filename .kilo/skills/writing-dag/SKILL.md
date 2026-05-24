---
name: writing-dag
description: Use when creating a new Dagster-based data pipeline with the layered architecture (entrypoints, containers, services, adapters/repositories), or when adding a new data source, transformation, or research workflow to an existing DAG package
---

# Writing DAGs

## Overview

Every pipeline follows a strict layered architecture: **Entrypoint → Container → Service → Adapter**. Dependency injection via `that-depends` wires the layers. A DAG may load data into storage (DLH), transform data for analytics (DWH), or gather and analyze data for research — the structure stays the same.

## Directory Structure

Applies everywhere DAGs live — `home/idata/dags/` or any other subtree:

```
<dags_package>/
  settings.py                     # Pydantic-settings; may extend IcebergSettingsBase for S3
  entrypoints/<domain>/           # CLI entrypoints, one per DAG
    __init__.py
    <entity>.py
  containers/<domain>/            # Dagster ops + @graph + Container class
    __init__.py
    <entity>.py
  services/<domain>/              # @define classes bridging containers ↔ adapters
    __init__.py
    <entity>.py
  adapters/<domain>/              # External systems: repositories/ for S3, clients/ for APIs
    __init__.py
    <entity>.py
```

All `__init__.py` files remain empty.

## Layer Responsibilities

| Layer | Role |
|-------|------|
| `settings.py` | Environment config; for S3 DAGs extends `IcebergSettingsBase` providing `catalog`, `uri`, S3 credentials |
| `adapters/` | Raw I/O — Iceberg scans, API calls, DuckDB queries — no business logic |
| `services/` | `attrs` `@define` classes; receive injected settings via `@inject` + `Provide["Alias.settings"]`, delegate to adapters |
| `containers/` | Dagster ops → `@graph` → `BaseContainer` with `Factory`/`Singleton`/`Dict` resource wiring |
| `entrypoints/` | `@Container.inject` → resolve `JobDefinition` → `execute_in_process()` |

## that-depends Tracing

```
Container.settings (Factory, auto-resolves env vars)
  → Provide["Alias.settings"]
    → Service methods receive settings

Container.job resource_defs
  → Dict("services": Dict("sdk_service": Factory(...), "dlh_service": Factory(...)))
    → settings → injected into Dagster resource context
```

## Idempotency

- **Iterative (append)**: source supports date-range queries → `MAX(timestamp)` from table → fetch only newer data → append. `CATCH_UP_DATE` as fallback on empty table.
- **Overwrite**: source returns full datasets → replace entire table each run.

See [`.kilo/skills/writing-dag/references/idempotency.md`](references/idempotency.md).

## Research DAGs (No Storage)

A DAG that gathers data for analysis without writing to Iceberg uses the same layers but skips:
- `IcebergSettingsBase` → plain `pydantic_settings.BaseSettings`
- `repositories/` → `adapters/clients/` for APIs
- `migrate_*` and `load_*` ops → replace with analysis/export ops

## Common Anti-patterns

- Modifying `_vN()` rather than adding `_vN+1()` — Iceberg schema evolution is additive
- Skipping `catalog.table_exists()` before writes
- Accessing SDK services directly in ops — use `context.resources.services["name"]`
- Adding content to `__init__.py` files
- Threading settings manually — use `@inject` + `Provide[...]` in services

## References

- [`.kilo/skills/writing-dag/references/settings.md`](references/settings.md) — settings hierarchy, IcebergSettingsBase, source-specific extensions
- [`.kilo/skills/writing-dag/references/container.md`](references/container.md) — Dagster ops, graph, BaseContainer wiring, service layer, entrypoints
- [`.kilo/skills/writing-dag/references/idempotency.md`](references/idempotency.md) — iterative (append) vs overwrite strategies
