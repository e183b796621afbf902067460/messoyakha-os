# pylint: disable=duplicate-code
from itertools import product
from typing import Callable
from uuid import uuid1
from warnings import filterwarnings

from boto3 import Session
from duckdb import DuckDBPyConnection
from loguru import logger
from numpy import ndarray
from pandas import DataFrame, Series
from pydantic import BaseModel
from talib import EMA, KAMA, SMA, TEMA

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

filterwarnings("ignore")


class _MainSchema(BaseModel):
    ohlc_service: OHLCService
    ma_service: MAService

    class Config:
        arbitrary_types_allowed = True


def compute_ma(data: DataFrame, ma_method: Callable[[ndarray, int], ndarray], ma_window: int, prefix: str) -> DataFrame:

    data[f"{prefix}_open"] = Series(ma_method(data["open"].values, ma_window))
    data[f"{prefix}_high"] = Series(ma_method(data["high"].values, ma_window))
    data[f"{prefix}_low"] = Series(ma_method(data["low"].values, ma_window))
    data[f"{prefix}_close"] = Series(ma_method(data["close"].values, ma_window))
    return data


def _compute_streak(data: DataFrame, is_ma_green_candle_column: str) -> DataFrame:
    prefix: str = f"streak_{is_ma_green_candle_column}"
    data["streak_start"] = data[is_ma_green_candle_column].ne(other=data[is_ma_green_candle_column].shift(1))
    data["streak_id"] = data["streak_start"].cumsum()
    data[prefix] = data.groupby("streak_id").cumcount() + 1

    data.drop(columns=["streak_start", "streak_id"], axis=1, inplace=True)
    return data


def _main(main_schema: _MainSchema) -> None:
    if main_schema.ohlc_service.ohlc is None:
        raise FileNotFoundError("There is no candlesticks data.")

    smooths: list[Callable[[ndarray, int], ndarray]] = [SMA, EMA, TEMA, KAMA]
    windows: list[int] = [2**2, 2**3, 2**4, 2**5]
    for smooth, window in product(smooths, windows):
        prefix: str = f"{smooth.__name__.lower()}_{window}"
        main_schema.ohlc_service.ohlc = compute_ma(
            data=main_schema.ohlc_service.ohlc, ma_method=smooth, ma_window=window, prefix=prefix
        )
        main_schema.ohlc_service.ohlc[f"is_{prefix}_green_candle"] = (
            main_schema.ohlc_service.ohlc[f"{prefix}_close"] > main_schema.ohlc_service.ohlc[f"{prefix}_open"]
        ).astype(int)
        main_schema.ohlc_service.ohlc = _compute_streak(
            data=main_schema.ohlc_service.ohlc, is_ma_green_candle_column=f"is_{prefix}_green_candle"
        )
        logger.info(f"{smooth.__name__}({window}) is ready.")
    main_schema.ohlc_service.ohlc.drop(columns=["open", "high", "low", "close", "close_time"], axis=1, inplace=True)
    main_schema.ohlc_service.ohlc.rename(columns={"open_time": "datetime"}, inplace=True)
    main_schema.ma_service.load_ma(dataframe=main_schema.ohlc_service.ohlc, filename=f"{uuid1()}.parquet")
    main_schema.ma_service.delete_object()


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
    _main(
        main_schema=_MainSchema(
            ohlc_service=OHLCService(
                s3_client=s3_client,
                repository=CandlesticksRepository(connection=duckdb_connection),
                query_parameters=OHLCQueryParametersSchema(
                    ticker=settings.TICKER,
                    exchange=settings.EXCHANGE,
                    section=settings.SECTION,
                    interval=settings.INTERVAL,
                ),
                path_parameters=OHLCPathParametersSchema(bucket=settings.S3_BUCKET),
            ),
            ma_service=MAService(
                s3_client=s3_client,
                repository=MARepository(connection=duckdb_connection),
                query_parameters=MAQueryParametersSchema(
                    ticker=settings.TICKER,
                    exchange=settings.EXCHANGE,
                    section=settings.SECTION,
                    interval=settings.INTERVAL,
                ),
                path_parameters=MAPathParametersSchema(bucket=settings.S3_BUCKET),
            ),
        )
    )


# pylint: enable=duplicate-code
