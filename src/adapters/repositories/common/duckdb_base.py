from typing import Any

from attr import attrs
from duckdb import DuckDBPyConnection
from pandas import DataFrame


@attrs(slots=True, auto_attribs=True, kw_only=True)
class DuckDBBaseRepository:
    _connection: DuckDBPyConnection

    def _query_dataframe(self, query: str, parameters: list[Any]) -> DataFrame:
        return self._connection.execute(query=query, parameters=parameters).df(
            date_as_object=True
        )

    def insert_dataframe_as_parquet(self, dataframe: DataFrame, key: str) -> None:
        dataframe = dataframe.copy(deep=True)
        self._connection.execute(
            query=f"COPY dataframe TO {key!r} (FORMAT PARQUET, COMPRESSION SNAPPY);"
        )
