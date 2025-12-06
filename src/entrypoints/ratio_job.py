# pylint: disable=duplicate-code
from typing import Final
from uuid import uuid1
from warnings import filterwarnings

from boto3 import Session
from collinearity import SelectNonCollinear
from duckdb import DuckDBPyConnection
from loguru import logger
from numpy import array, log1p, ndarray, tanh
from pandas import DataFrame, concat
from sklearn.feature_selection import f_regression
from sklearn.preprocessing import MinMaxScaler

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.indicators import MARepository, RatioRepository
from src.entrypoints.common.base import findall_prefixes
from src.schemas.filters import (
    MAPathParametersSchema,
    MAQueryParametersSchema,
    OHLCPathParametersSchema,
    OHLCQueryParametersSchema,
    RatioPathParametersSchema,
    RatioQueryParametersSchema,
)
from src.services.domain.s3 import MAService, OHLCService, RatioService
from src.settings import settings

# pylint: enable=duplicate-code

filterwarnings("ignore")

_CORRELATION_THRESHOLD: Final[float] = 0.99


# pylint: disable=redefined-outer-name
def _compute_ratio(data: DataFrame, moving_average_prefix: str) -> DataFrame:
    prefix: str = f"ratio_{moving_average_prefix}_to_price"

    data["_ma_average_price"] = (
        data[f"{moving_average_prefix}_open"]
        + data[f"{moving_average_prefix}_high"]
        + data[f"{moving_average_prefix}_low"]
        + data[f"{moving_average_prefix}_close"]
    ) / 4
    data[prefix] = data["_ma_average_price"] / data["average_price"] - 1
    data.drop(
        columns=["_ma_average_price"],
        axis=1,
        inplace=True,
    )
    return data


def _handle_outlier(ratio: float, plus_sigma: float, minus_sigma: float) -> float:
    if ratio > plus_sigma:
        return plus_sigma
    if ratio < minus_sigma:
        return minus_sigma
    return ratio


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
    ratio_service: RatioService = RatioService(
        s3_client=s3_client,
        repository=RatioRepository(connection=duckdb_connection),
        query_parameters=RatioQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=RatioPathParametersSchema(bucket=settings.S3_BUCKET, directory="ratios"),
    )

    feature_selector: SelectNonCollinear = SelectNonCollinear(
        correlation_threshold=_CORRELATION_THRESHOLD, scoring=f_regression
    )
    feature_scaler: MinMaxScaler = MinMaxScaler()

    candlesticks: DataFrame | None = ohlc_service.extract_ohlc()
    if candlesticks is None:
        raise FileNotFoundError("There is no candlesticks data.")
    candlesticks.drop_duplicates(inplace=True)
    candlesticks.rename(mapper={"open_time": "datetime"}, axis=1, inplace=True)
    candlesticks["average_price"] = (
        candlesticks["open"] + candlesticks["high"] + candlesticks["low"] + candlesticks["close"]
    ) / 4
    candlesticks.drop(columns=["open", "high", "low", "close", "close_time"], axis=1, inplace=True)

    moving_averages: DataFrame | None = ma_service.extract_ma()
    if moving_averages is None:
        raise FileNotFoundError("There is no moving averages data.")
    moving_averages.drop_duplicates(inplace=True)

    moving_averages = moving_averages.merge(
        right=candlesticks, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )

    moving_average_prefixes: list[str] = findall_prefixes(strings=moving_averages.columns.to_list())
    for moving_average_prefix in moving_average_prefixes:
        moving_averages = _compute_ratio(data=moving_averages, moving_average_prefix=moving_average_prefix)

    moving_averages.drop(columns=["average_price"], axis=1, inplace=True)
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
    moving_averages.dropna(inplace=True)

    feature_columns: list[str] = [column for column in moving_averages.columns.tolist() if column.startswith("ratio")]
    feature_values: ndarray = moving_averages[feature_columns].values

    feature_selector.fit(X=feature_values)

    ratio_columns: list[str] = array(feature_columns)[feature_selector.get_support()].tolist()
    ratios: DataFrame = moving_averages[ratio_columns].copy(deep=True)

    ratios["exchange"] = settings.EXCHANGE
    ratios["section"] = settings.SECTION
    ratios["ticker"] = settings.TICKER
    ratios["interval"] = settings.INTERVAL
    ratios["datetime"] = moving_averages["datetime"].values
    ratios["year"] = ratios["datetime"].dt.year

    train: DataFrame = ratios.query(f"year < {settings.TRIGGER_DATE.year - 1}")
    validation: DataFrame = ratios.query(f"year >= {settings.TRIGGER_DATE.year - 1}")

    train[ratio_columns] = log1p(tanh(train[ratio_columns]))
    validation[ratio_columns] = log1p(tanh(validation[ratio_columns]))

    # pylint: disable=cell-var-from-loop
    for ratio_column in ratio_columns:  # noqa: WPS426
        mean: float = train[ratio_column].mean()
        std: float = train[ratio_column].std()

        plus_sigma: float = mean + 3 * std
        minus_sigma: float = mean - 3 * std

        train[ratio_column] = train[ratio_column].apply(
            lambda ratio: _handle_outlier(ratio=ratio, plus_sigma=plus_sigma, minus_sigma=minus_sigma)
        )
        validation[ratio_column] = validation[ratio_column].apply(
            lambda ratio: _handle_outlier(ratio=ratio, plus_sigma=plus_sigma, minus_sigma=minus_sigma)
        )
    # pylint: disable=cell-var-from-loop

    feature_scaler.fit(X=train[ratio_columns])

    train[ratio_columns] = feature_scaler.transform(X=train[ratio_columns])
    validation[ratio_columns] = feature_scaler.transform(X=validation[ratio_columns])

    # pylint: disable=cell-var-from-loop
    for ratio_column in ratio_columns:  # noqa: WPS426 WPS440
        validation[ratio_column] = validation.apply(
            lambda row: min(row[ratio_column], 1)
            if row[ratio_column] > 1
            else max(row[ratio_column], 0),  # noqa: WPS221
            axis=1,
        )  # noqa: B023

    # pylint: enable=cell-var-from-loop

    ratios = concat(objs=[train, validation])
    ratios.sort_values(by="datetime", inplace=True)
    logger.info(f"There are {len(ratio_columns)} features in total.")
    logger.info(f"The features are: {ratio_columns}.")

    ratios.to_csv("train.csv", index=False)

    ratio_service.load_ratio(dataframe=ratios, filename=f"{uuid1()}.parquet")
    ratio_service.delete_object()


# pylint: enable=duplicate-code
