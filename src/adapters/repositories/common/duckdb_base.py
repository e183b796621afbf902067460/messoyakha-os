from typing import Any

from attr import attrs
from duckdb import DuckDBPyConnection, connect
from pandas import DataFrame


def get_duckdb_connection(
    s3_access_key_id: str, s3_secret_access_key: str, s3_endpoint_url: str, s3_region_name: str
) -> DuckDBPyConnection:
    duckdb_connection: DuckDBPyConnection = connect(database=":memory")

    duckdb_connection.execute(query="INSTALL httpfs;")
    duckdb_connection.execute(query="LOAD httpfs;")

    duckdb_connection.execute(query=f"SET s3_access_key_id={s3_access_key_id!r};")
    duckdb_connection.execute(query=f"SET s3_secret_access_key={s3_secret_access_key!r};")
    duckdb_connection.execute(query=f"SET s3_endpoint={s3_endpoint_url!r};")
    duckdb_connection.execute(query=f"SET s3_region={s3_region_name!r};")

    return duckdb_connection


@attrs(slots=True, auto_attribs=True, kw_only=True)
class DuckDBBaseRepository:

    _connection: DuckDBPyConnection

    def _query_dataframe(self, query: str, parameters: list[Any]) -> DataFrame:
        return self._connection.execute(query=query, parameters=parameters).df(date_as_object=True)

    def insert_dataframe_as_parquet(self, dataframe: DataFrame, key: str) -> None:
        dataframe = dataframe.copy(deep=True)
        self._connection.execute(query=f"COPY dataframe TO {key!r} (FORMAT PARQUET, COMPRESSION SNAPPY);")
