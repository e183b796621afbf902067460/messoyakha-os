from duckdb import (
    DuckDBPyConnection,
    connect as duckdb_connect,
)
from pydantic import HttpUrl


def connect(access_key: str, secret_key: str, endpoint: HttpUrl, region: str) -> DuckDBPyConnection:
    connection: DuckDBPyConnection = duckdb_connect(database=":memory")

    connection.execute(query="INSTALL httpfs; LOAD httpfs;")
    connection.execute(query="INSTALL iceberg; LOAD iceberg;")

    connection.execute(query="SET unsafe_enable_version_guessing=true;")

    connection.execute(query=f"SET s3_access_key_id={access_key!r};")
    connection.execute(query=f"SET s3_secret_access_key={secret_key!r};")
    connection.execute(query=f"SET s3_endpoint={endpoint.unicode_host()!r};")
    connection.execute(query=f"SET s3_region={region!r};")
    return connection
