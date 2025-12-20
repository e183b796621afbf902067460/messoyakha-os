# pylint: disable=duplicate-code
from itertools import product
from typing import Final
from uuid import uuid1
from warnings import filterwarnings

from boto3 import Session
from collinearity import SelectNonCollinear
from duckdb import DuckDBPyConnection
from loguru import logger
from numpy import array, ndarray
from pandas import DataFrame
from pydantic import BaseModel
from sklearn.feature_selection import f_regression
from talib import RSI

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.indicators import MARepository, RSIRepository
from src.schemas.filters import (
    MAPathParametersSchema,
    MAQueryParametersSchema,
    RSIPathParametersSchema,
    RSIQueryParametersSchema,
)
from src.services.domain.s3 import MAService, RSIService
from src.settings import settings

# pylint: enable=duplicate-code

filterwarnings("ignore")


_CORRELATION_THRESHOLD: Final[float] = 0.9


class _MainSchema(BaseModel):
    ma_service: MAService
    rsi_service: RSIService

    selector: SelectNonCollinear

    class Config:
        arbitrary_types_allowed = True


def compute_rsi(data: DataFrame, ma_prefix: str, rsi_window: int) -> DataFrame:
    data["avg_price"] = (
        data[f"{ma_prefix}_open"] + data[f"{ma_prefix}_high"] + data[f"{ma_prefix}_low"] + data[f"{ma_prefix}_close"]
    ) / 4
    data[f"rsi_{rsi_window}_{ma_prefix}"] = abs(RSI(real=data["avg_price"], timeperiod=rsi_window) / 10**2)
    data.drop(columns=["avg_price"], axis=1, inplace=True)
    return data


# pylint: disable=duplicate-code
def _main(main_schema: _MainSchema) -> None:
    if main_schema.ma_service.ma is None:
        raise FileNotFoundError("There is no moving averages data.")

    rsi_windows: list[int] = [2**3, 2**4, 2**5, 2**6, 2**7, 2**8]
    for ma_prefix, rsi_window in product(main_schema.ma_service.ma_prefixes, rsi_windows):  # type: ignore[arg-type]
        main_schema.ma_service.ma = compute_rsi(
            data=main_schema.ma_service.ma, ma_prefix=ma_prefix, rsi_window=rsi_window
        )
    main_schema.ma_service.ma.drop(
        columns=[
            column
            for column in main_schema.ma_service.ma.columns.to_list()
            for ma_prefix in main_schema.ma_service.ma_prefixes  # type: ignore[union-attr]
            if column.startswith(ma_prefix) or column == f"is_{ma_prefix}" or column == f"r_{ma_prefix}"  # noqa: WPS441
        ],
        axis=1,
        inplace=True,
    )
    main_schema.ma_service.ma.dropna(inplace=True)

    rsi_columns: list[str] = main_schema.rsi_service.get_rsi_columns(columns=main_schema.ma_service.ma.columns.tolist())
    rsi_values: ndarray = main_schema.ma_service.ma[rsi_columns].values
    main_schema.selector.fit(X=rsi_values)

    selected_columns: list[str] = array(rsi_columns)[main_schema.selector.get_support()].tolist()
    rsi: DataFrame = main_schema.ma_service.ma[selected_columns].copy(deep=True)
    rsi["exchange"] = settings.EXCHANGE
    rsi["section"] = settings.SECTION
    rsi["ticker"] = settings.TICKER
    rsi["interval"] = settings.INTERVAL
    rsi["datetime"] = main_schema.ma_service.ma["datetime"].values
    rsi["year"] = rsi["datetime"].dt.year
    rsi.sort_values(by="datetime", inplace=True)
    logger.info(f"There are {len(selected_columns)} features in total.")

    main_schema.rsi_service.load_rsi(dataframe=rsi, filename=f"{uuid1()}.parquet")
    main_schema.rsi_service.delete_object()


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
            rsi_service=RSIService(
                s3_client=s3_client,
                repository=RSIRepository(connection=duckdb_connection),
                query_parameters=RSIQueryParametersSchema(
                    ticker=settings.TICKER,
                    exchange=settings.EXCHANGE,
                    section=settings.SECTION,
                    interval=settings.INTERVAL,
                ),
                path_parameters=RSIPathParametersSchema(bucket=settings.S3_BUCKET),
            ),
            selector=SelectNonCollinear(scoring=f_regression, correlation_threshold=_CORRELATION_THRESHOLD),
        )
    )

# pylint: enable=duplicate-code
