from abc import ABC
from typing import Any

from attr import define
from duckdb import DuckDBPyConnection
from polars import DataFrame


@define(slots=False, auto_attribs=True, kw_only=True)
class DuckDBIcebergS3RepositoryBase(ABC):
    _connection: DuckDBPyConnection

    def _query_pl(self, query: str, parameters: list[Any] | None = None) -> DataFrame:
        return self._connection.execute(query=query, parameters=parameters).pl()

    def _query_one(self, query: str, parameters: list[Any] | None = None) -> Any:
        return self._connection.execute(query=query, parameters=parameters).fetchone()
