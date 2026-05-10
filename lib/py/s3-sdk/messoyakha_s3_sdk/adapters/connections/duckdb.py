from duckdb import (
    DuckDBPyConnection,
    connect as duckdb_connect,
)


def connect(access_key: str, secret_key: str, endpoint: str, region: str) -> DuckDBPyConnection:
    connection: DuckDBPyConnection = duckdb_connect(database=":memory")

    connection.execute(query="INSTALL httpfs; LOAD httpfs;")
    connection.execute(query="INSTALL iceberg; LOAD iceberg;")

    connection.execute(query=f"SET s3_access_key_id={access_key!r};")
    connection.execute(query=f"SET s3_secret_access_key={secret_key!r};")
    connection.execute(query=f"SET s3_endpoint={endpoint!r};")
    connection.execute(query=f"SET s3_region={region!r};")
    return connection
