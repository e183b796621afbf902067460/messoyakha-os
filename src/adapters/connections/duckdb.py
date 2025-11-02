from duckdb import DuckDBPyConnection, connect


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
