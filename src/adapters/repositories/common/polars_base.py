from attr import attrs
from polars import LazyFrame, scan_parquet


@attrs(slots=True, auto_attribs=True, kw_only=True)
class PolarsBaseRepository:
    _storage_options: dict[str, str]

    def _scan_parquet(self, path: str) -> LazyFrame:
        return scan_parquet(source=path, extra_columns="ignore", storage_options=self._storage_options)

    def _scan_parquets(self, paths: list[str]) -> list[LazyFrame]:
        return [self._scan_parquet(path=path) for path in paths]

    def scan(self, paths: str | list[str]) -> LazyFrame | list[LazyFrame]:
        if isinstance(paths, str):
            return self._scan_parquet(path=paths)
        return self._scan_parquets(paths=paths)
