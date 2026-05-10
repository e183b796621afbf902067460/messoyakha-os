from abc import ABC
from typing import Any

from attr import define
from duckdb import DuckDBPyConnection
from polars import DataFrame


@define(slots=True, auto_attribs=True, kw_only=True)
class DuckDBIcebergS3RepositoryBase(ABC):
    _connection: DuckDBPyConnection

    def _query(self, query: str, parameters: list[Any]) -> DataFrame:
        return self._connection.execute(query=query, parameters=parameters).pl()
