# pylint: disable=duplicate-code
from typing import Callable
from uuid import uuid1

from boto3 import Session
from duckdb import DuckDBPyConnection
from numpy import ndarray
from pandas import DataFrame, Series
from talib import DEMA, EMA, KAMA, SMA, TEMA, TRIMA

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.indicators import MARepository
from src.schemas.filters import (
    MAPathParametersSchema,
    MAQueryParametersSchema,
    OHLCPathParametersSchema,
    OHLCQueryParametersSchema,
)
from src.services.domain.s3 import MAService, OHLCService
from src.settings import settings

# pylint: enable=duplicate-code


# pylint: disable=redefined-outer-name
def _compute_moving_average(
    data: DataFrame, moving_average_method: Callable[[ndarray, int], ndarray], moving_average_window: int
) -> DataFrame:
    prefix: str = f"{moving_average_method.__name__.lower()}_{moving_average_window}"

    data[f"{prefix}_open"] = Series(moving_average_method(data.open.values, moving_average_window))
    data[f"{prefix}_high"] = Series(moving_average_method(data.high.values, moving_average_window))
    data[f"{prefix}_low"] = Series(moving_average_method(data.low.values, moving_average_window))
    data[f"{prefix}_close"] = Series(moving_average_method(data.close.values, moving_average_window))
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
    ohlc_service: OHLCService = OHLCService(
        s3_client=s3_client,
        repository=CandlesticksRepository(connection=duckdb_connection),
        query_parameters=OHLCQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=OHLCPathParametersSchema(bucket=settings.S3_BUCKET, directory="candlesticks"),
    )
    ma_service: MAService = MAService(
        s3_client=s3_client,
        repository=MARepository(connection=duckdb_connection),
        query_parameters=MAQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=MAPathParametersSchema(bucket=settings.S3_BUCKET, directory="moving-averages"),
    )

    candlesticks: DataFrame | None = ohlc_service.extract_ohlc()
    if candlesticks is None:
        raise FileNotFoundError("There is no candlesticks data.")
    candlesticks.drop_duplicates(inplace=True)

    moving_average_methods: list[Callable[[ndarray, int], ndarray]] = [SMA, TRIMA, EMA, DEMA, TEMA, KAMA]
    moving_average_windows: list[int] = [2**2, 2**4, 2**6, 2**8, 2**10]
    for moving_average_method in moving_average_methods:
        for moving_average_window in moving_average_windows:
            candlesticks = _compute_moving_average(
                data=candlesticks,
                moving_average_method=moving_average_method,
                moving_average_window=moving_average_window,
            )
    candlesticks.drop(columns=["open", "high", "low", "close", "close_time"], axis=1, inplace=True)
    candlesticks.rename(columns={"open_time": "datetime"}, inplace=True)

    moving_averages: DataFrame = candlesticks.copy(deep=True)
    ma_service.load_dataframe_as_parquet(dataframe=moving_averages, filename=f"{uuid1()}.parquet")
    ma_service.delete_object()


# pylint: enable=duplicate-code
