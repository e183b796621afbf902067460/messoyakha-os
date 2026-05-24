# Idempotency

## Decision

| Factor | Iterative | Overwrite |
|--------|-----------|-----------|
| Source has date-range parameters | Yes | No |
| Write mode | `"append"` | `"overwrite"` |
| `query_latest_timestamp` op | Required | Not needed |
| `CATCH_UP_DATE` setting | Required | Not needed |
| Safe to rerun | Yes (`>` filter) | Yes (replaced) |

## Iterative (Append)

For sources that accept `start_time`/`end_time` parameters. Op flow:

```
migrate → query_latest_timestamp → get_data → load_data
```

**query_latest_timestamp**: queries `MAX(timestamp)` from the Iceberg table via DuckDB `iceberg_scan`. Falls back to `CATCH_UP_DATE` when the table is empty or doesn't exist yet. This date becomes the `start_time` for the data fetch.

```python
def query_latest_timestamp(self, uri, catalog, namespace, catch_up_date):
    if catalog.table_exists(...):
        path = f"{uri}/{namespace}.{self._namespace}/{self._table}"
        query = f"SELECT MAX(timestamp) FROM iceberg_scan({path!r})"
        return self._query_one(query=query)[0].replace(tzinfo=timezone.utc)
    return catch_up_date
```

**get_data**: fetches from SDK using the latest timestamp as lower bound, TRIGGER_DATE as upper bound. Applies strict `col("timestamp") > latest_timestamp` filter to prevent re-inserting the boundary row.

**load_data**: writes via `write_iceberg(mode="append")`, guarded by `catalog.table_exists()` and `not df.is_empty()`.

**Settings** must include `CATCH_UP_DATE` — the earliest date from which to start gathering if the table has never been loaded.

## Overwrite

For sources that return full datasets each run. Op flow:

```
migrate → (fan-out crawl) → load_data
```

**No `query_latest_timestamp` step**. The data fetch returns the complete dataset on every run.

**load_data**: writes via `write_iceberg(mode="overwrite")`, guarded by `catalog.table_exists()`.

**Settings** omit `CATCH_UP_DATE`.
