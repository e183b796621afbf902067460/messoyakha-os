from uuid import uuid1

from boto3 import Session
from duckdb import DuckDBPyConnection
from pandas import DataFrame
from talib import AROONOSC

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.indicators import AroonRepository, MARepository
from src.entrypoints.commmon.base import findall_prefixes
from src.schemas.filters import (
    AroonPathParametersSchema,
    AroonQueryParametersSchema,
    MAPathParametersSchema,
    MAQueryParametersSchema,
)
from src.services.domain.s3 import AroonService, MAService
from src.settings import settings


# pylint: disable=redefined-outer-name
def _compute_aroon(data: DataFrame, moving_average_prefix: str, aroon_window: int) -> DataFrame:
    prefix: str = f"aroon_{aroon_window}_{moving_average_prefix}"

    data[prefix] = abs(
        AROONOSC(
            high=data[f"{moving_average_prefix}_high"],
            low=data[f"{moving_average_prefix}_low"],
            timeperiod=aroon_window,
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

    ma_service: MAService = MAService(
        s3_client=s3_client,
        repository=MARepository(connection=duckdb_connection),
        query_parameters=MAQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=MAPathParametersSchema(bucket=settings.S3_BUCKET, directory="moving-averages"),
    )
    aroon_service: AroonService = AroonService(
        s3_client=s3_client,
        repository=AroonRepository(connection=duckdb_connection),
        query_parameters=AroonQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=AroonPathParametersSchema(bucket=settings.S3_BUCKET, directory="aroons"),
    )

    moving_averages: DataFrame | None = ma_service.extract_ma()
    if moving_averages is None:
        raise FileNotFoundError("There is no moving averages data.")
    moving_averages.drop_duplicates(inplace=True)

    moving_average_prefixes: list[str] = findall_prefixes(strings=moving_averages.columns.to_list())
    aroon_windows: list[int] = [2**2, 2**4, 2**6, 2**8]
    for moving_average_prefix in moving_average_prefixes:
        for aroon_window in aroon_windows:
            moving_averages = _compute_aroon(
                data=moving_averages,
                moving_average_prefix=moving_average_prefix,
                aroon_window=aroon_window,
            )
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
    aroons: DataFrame = moving_averages.copy(deep=True)
    aroon_service.load_dataframe_as_parquet(dataframe=aroons, filename=f"{uuid1()}.parquet")
    aroon_service.delete_object()


# pylint: enable=duplicate-code
