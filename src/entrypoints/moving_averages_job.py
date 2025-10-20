from typing import Callable
from uuid import uuid1

from boto3 import Session
from duckdb import DuckDBPyConnection
from numpy import ndarray
from pandas import DataFrame, Series
from talib import DEMA, EMA, KAMA, SMA, TEMA, TRIMA

from src.adapters.clients.s3 import S3Client
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.common.duckdb_base import get_duckdb_connection
from src.adapters.repositories.moving_averages import MovingAveragesRepository
from src.schemas.domain.s3 import ListObjectsResponseSchema
from src.schemas.queries import CandlesticksQueryParametersSchema
from src.services.common.misc import format_s3_key, format_s3_path
from src.settings import settings


def _compute_moving_average(
    data: DataFrame, moving_average_method: Callable[[ndarray, int], ndarray], moving_average_window: int
) -> DataFrame:
    prefix: str = f"{moving_average_method.__name__.lower()}_{moving_average_window}"

    data[f"{prefix}_open"] = Series(moving_average_method(data.open.values, moving_average_window))
    data[f"{prefix}_high"] = Series(moving_average_method(data.high.values, moving_average_window))
    data[f"{prefix}_low"] = Series(moving_average_method(data.low.values, moving_average_window))
    data[f"{prefix}_close"] = Series(moving_average_method(data.close.values, moving_average_window))
    return data


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
    candlesticks_repository: CandlesticksRepository = CandlesticksRepository(connection=duckdb_connection)
    moving_averages_repository: MovingAveragesRepository = MovingAveragesRepository(connection=duckdb_connection)

    s3_candlesticks_path: str = format_s3_path(
        exchange=settings.EXCHANGE, section=settings.SECTION, directory="candlesticks"
    )
    s3_moving_averages_path: str = format_s3_path(
        exchange=settings.EXCHANGE, section=settings.SECTION, directory="moving-averages"
    )
    list_candlesticks_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="candlesticks"),
    )
    list_moving_averages_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="moving-averages"),
    )

    candlesticks: DataFrame | None = candlesticks_repository.query_candlesticks(
        parameters_schema=CandlesticksQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path=(
            f"{s3_candlesticks_path}/{list_candlesticks_objects_response.filename}"
            if list_candlesticks_objects_response.filename
            else f"{s3_candlesticks_path}/"
        ),
    )
    if candlesticks is None:
        raise FileNotFoundError(f"There is no candlesticks data in {s3_candlesticks_path}.")
    candlesticks.drop_duplicates(inplace=True)

    moving_averages_methods: list[Callable[[ndarray, int], ndarray]] = [SMA, TRIMA, EMA, DEMA, TEMA, KAMA]
    moving_averages_windows: list[int] = [2**2, 2**4, 2**6, 2**8, 2**10]
    for moving_averages_method in moving_averages_methods:
        for moving_averages_window in moving_averages_windows:
            candlesticks = _compute_moving_average(
                data=candlesticks,
                moving_average_method=moving_averages_method,
                moving_average_window=moving_averages_window,
            )
    candlesticks.drop(columns=["open", "high", "low", "close", "close_time"], axis=1, inplace=True)
    candlesticks.rename(columns={"open_time": "datetime"}, inplace=True)

    moving_averages_repository.insert_dataframe_as_parquet(
        dataframe=candlesticks, key=f"{s3_moving_averages_path}/{uuid1()}.parquet"
    )
    if list_moving_averages_objects_response.filename:
        s3_client.delete_object(
            bucket=settings.S3_BUCKET,
            key=format_s3_key(
                exchange=settings.EXCHANGE,
                section=settings.SECTION,
                directory="moving-averages",
                filename=list_moving_averages_objects_response.filename,
            ),
        )

# pylint: enable=duplicate-code
