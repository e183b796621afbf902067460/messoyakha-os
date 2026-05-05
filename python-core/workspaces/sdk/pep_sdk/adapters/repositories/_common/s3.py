from typing import Any

from attr import define
from duckdb import DuckDBPyConnection, connect
from polars import DataFrame


def duckdb_s3_connection(access_key: str, secret_key: str, endpoint: str, region: str) -> DuckDBPyConnection:
    connection: DuckDBPyConnection = connect(database=":memory")

    connection.execute(query="INSTALL httpfs; LOAD httpfs;")
    connection.execute(query="INSTALL iceberg; LOAD iceberg;")

    connection.execute(query=f"SET s3_access_key_id={access_key!r};")
    connection.execute(query=f"SET s3_secret_access_key={secret_key!r};")
    connection.execute(query=f"SET s3_endpoint={endpoint!r};")
    connection.execute(query=f"SET s3_region={region!r};")
    return connection


@define(slots=True, auto_attribs=True, kw_only=True)
class DuckDBS3RepositoryBase:
    _connection: DuckDBPyConnection

    def _query(self, query: str, parameters: list[Any]) -> DataFrame:
        return self._connection.execute(query=query, parameters=parameters).pl()

    def _insert(self, dataframe: DataFrame, path: str) -> None: ...
