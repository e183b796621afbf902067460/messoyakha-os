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
from pydantic import BaseModel, Field
from sklearn.feature_selection import f_regression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from talib import ADX

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.indicators import ADXRepository, MARepository
from src.schemas.filters import (
    ADXPathParametersSchema,
    ADXQueryParametersSchema,
    MAPathParametersSchema,
    MAQueryParametersSchema,
)
from src.services.domain.s3 import ADXService, MAService
from src.settings import settings

# pylint: enable=duplicate-code

filterwarnings("ignore")


_CORRELATION_THRESHOLD: Final[float] = 0.75


class _MainSchema(BaseModel):
    ma_service: MAService
    adx_service: ADXService

    selector: SelectNonCollinear
    scaler: MinMaxScaler = Field(default_factory=MinMaxScaler)

    class Config:
        arbitrary_types_allowed = True


def compute_adx(data: DataFrame, ma_prefix: str, adx_window: int) -> DataFrame:
    data[f"adx_{adx_window}_{ma_prefix}"] = abs(
        ADX(
            high=data[f"{ma_prefix}_high"],
            low=data[f"{ma_prefix}_low"],
            close=data[f"{ma_prefix}_close"],
            timeperiod=adx_window,
        )
        / 10**2
    )
    return data


# pylint: disable=duplicate-code, too-many-locals, too-many-statements
def _main(main_schema: _MainSchema) -> None:
    if main_schema.ma_service.ma is None:
        raise FileNotFoundError("There is no moving averages data.")

    adx_windows: list[int] = [2**2, 2**3, 2**4, 2**5]
    for ma_prefix, adx_window in product(main_schema.ma_service.ma_prefixes, adx_windows):  # type: ignore[arg-type]
        main_schema.ma_service.ma = compute_adx(
            data=main_schema.ma_service.ma,
            ma_prefix=ma_prefix,
            adx_window=adx_window,
        )
    main_schema.ma_service.ma.drop(
        columns=[
            column
            for column in main_schema.ma_service.ma.columns.to_list()
            for ma_prefix in main_schema.ma_service.ma_prefixes  # type: ignore[union-attr]
            if column.startswith(ma_prefix)  # noqa: WPS441
            or column == f"is_{ma_prefix}"  # noqa: WPS441
            or column == f"streak_{ma_prefix}"  # noqa: WPS441
        ],
        axis=1,
        inplace=True,
    )
    main_schema.ma_service.ma.dropna(inplace=True)

    adx_columns: list[str] = main_schema.adx_service.get_adx_columns(columns=main_schema.ma_service.ma.columns.tolist())
    adx_values: ndarray = main_schema.ma_service.ma[adx_columns].values
    main_schema.selector.fit(X=adx_values)

    selected_columns: list[str] = array(adx_columns)[main_schema.selector.get_support()].tolist()
    adx: DataFrame = main_schema.ma_service.ma[selected_columns].copy(deep=True)
    adx["exchange"] = settings.EXCHANGE
    adx["section"] = settings.SECTION
    adx["ticker"] = settings.TICKER
    adx["interval"] = settings.INTERVAL
    adx["datetime"] = main_schema.ma_service.ma["datetime"].values
    adx["year"] = adx["datetime"].dt.year
    adx.sort_values(by="datetime", inplace=True)
    logger.info(f"There are {len(selected_columns)} features in total.")

    train_adx, _, _, _ = train_test_split(
        adx, adx[["ticker"]], train_size=settings.TRAIN_SIZE, random_state=settings.RANDOM_STATE, shuffle=False
    )
    main_schema.scaler.fit(X=train_adx[selected_columns])
    adx[selected_columns] = main_schema.scaler.transform(X=adx[selected_columns])

    main_schema.adx_service.load_adx(dataframe=adx, filename=f"{uuid1()}.parquet")
    main_schema.adx_service.delete_object()


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
            adx_service=ADXService(
                s3_client=s3_client,
                repository=ADXRepository(connection=duckdb_connection),
                query_parameters=ADXQueryParametersSchema(
                    ticker=settings.TICKER,
                    exchange=settings.EXCHANGE,
                    section=settings.SECTION,
                    interval=settings.INTERVAL,
                ),
                path_parameters=ADXPathParametersSchema(bucket=settings.S3_BUCKET),
            ),
            selector=SelectNonCollinear(scoring=f_regression, correlation_threshold=_CORRELATION_THRESHOLD),
        )
    )


# pylint: enable=duplicate-code, too-many-locals, too-many-statements
