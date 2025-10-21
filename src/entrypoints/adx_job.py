from uuid import uuid1

from boto3 import Session
from duckdb import DuckDBPyConnection
from pandas import DataFrame
from talib import ADX

from src.adapters.clients.s3 import S3Client
from src.adapters.repositories.adx import ADXRepository
from src.adapters.repositories.common.duckdb_base import get_duckdb_connection
from src.adapters.repositories.moving_averages import MovingAveragesRepository
from src.schemas.domain.s3 import ListObjectsResponseSchema
from src.schemas.queries import MovingAveragesQueryParametersSchema
from src.services.common.misc import findall_prefixes, format_s3_key, format_s3_path
from src.settings import settings


# pylint: disable=redefined-outer-name
def _compute_adx(data: DataFrame, moving_average_prefix: str, adx_window: int) -> DataFrame:
    prefix: str = f"adx_{adx_window}_{moving_average_prefix}"

    data[prefix] = abs(
        ADX(
            high=data[f"{moving_average_prefix}_high"],
            low=data[f"{moving_average_prefix}_low"],
            close=data[f"{moving_average_prefix}_close"],
            timeperiod=adx_window,
        )
        / 10**2
    )
    return data


# pylint: enable=redefined-outer-name


# pylint: disable=duplicate-code
if __name__ == "__main__":
    s3_client: S3Client = S3Client(
        session=Session(
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION_NAME,
        )
    )
    duckdb_connection: DuckDBPyConnection = get_duckdb_connection(
        s3_access_key_id=settings.S3_ACCESS_KEY_ID,
        s3_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        s3_endpoint_url=settings.S3_ENDPOINT_URL.host,
        s3_region_name=settings.S3_REGION_NAME,
    )
    moving_averages_repository: MovingAveragesRepository = MovingAveragesRepository(connection=duckdb_connection)
    adx_repository: ADXRepository = ADXRepository(connection=duckdb_connection)

    s3_moving_averages_path: str = format_s3_path(
        exchange=settings.EXCHANGE, section=settings.SECTION, directory="moving-averages"
    )
    s3_adx_path: str = format_s3_path(exchange=settings.EXCHANGE, section=settings.SECTION, directory="adx")
    list_moving_averages_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="moving-averages"),
    )
    list_adx_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="adx"),
    )

    moving_averages: DataFrame | None = moving_averages_repository.query_moving_averages(
        parameters_schema=MovingAveragesQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path=(
            f"{s3_moving_averages_path}/{list_moving_averages_objects_response.filename}"
            if list_moving_averages_objects_response.filename
            else f"{list_moving_averages_objects_response}/"
        ),
    )
    if moving_averages is None:
        raise FileNotFoundError(f"There is no moving averages data in {s3_moving_averages_path}.")
    moving_averages.drop_duplicates(inplace=True)

    moving_average_prefixes: list[str] = findall_prefixes(strings=moving_averages.columns.to_list())
    adx_windows: list[int] = [2**2, 2**4, 2**6, 2**8]
    for moving_average_prefix in moving_average_prefixes:
        for adx_window in adx_windows:
            moving_averages = _compute_adx(
                data=moving_averages, moving_average_prefix=moving_average_prefix, adx_window=adx_window
            )

    column: str
    moving_averages.drop(
        columns=[
            column
            for column in moving_averages.columns.to_list()
            for prefix in moving_average_prefixes
            if column.startswith(prefix)
        ],
        axis=1,
        inplace=True,
    )

    adx_repository.insert_dataframe_as_parquet(dataframe=moving_averages, key=f"{s3_adx_path}/{uuid1()}.parquet")
    if list_adx_objects_response.filename:
        s3_client.delete_object(
            bucket=settings.S3_BUCKET,
            key=format_s3_key(
                exchange=settings.EXCHANGE,
                section=settings.SECTION,
                directory="adx",
                filename=list_adx_objects_response.filename,
            ),
        )

# pylint: enable=duplicate-code
