from re import findall
from uuid import uuid1

from boto3 import Session
from duckdb import DuckDBPyConnection
from pandas import DataFrame
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


def _findall_prefixes(strings: list[str]) -> list[str]:
    pattern: str = r"\b([a-zA-Z]+_\d+)_(?:open|high|low|close)\b"

    prefixes: list[str] = []
    for string in strings:
        match: list[str] = findall(pattern=pattern, string=string)
        if match and match[0] not in prefixes:
            prefixes.append(match[0])
    return prefixes


# pylint: disable=redefined-outer-name
def _compute_average_directional_index(
    data: DataFrame, moving_average_prefix: str, average_directional_index_window: int
) -> DataFrame:
    prefix: str = f"adx_{average_directional_index_window}_{moving_average_prefix}"

    data[prefix] = abs(
        ADX(
            high=data[f"{moving_average_prefix}_high"],
            low=data[f"{moving_average_prefix}_low"],
            close=data[f"{moving_average_prefix}_close"],
            timeperiod=average_directional_index_window,
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
    adx_service: ADXService = ADXService(
        s3_client=s3_client,
        repository=ADXRepository(connection=duckdb_connection),
        query_parameters=ADXQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=ADXPathParametersSchema(bucket=settings.S3_BUCKET, directory="average-directional-indexes"),
    )

    moving_averages: DataFrame | None = ma_service.extract_ma()
    if moving_averages is None:
        raise FileNotFoundError("There is no moving averages data.")
    moving_averages.drop_duplicates(inplace=True)

    moving_average_prefixes: list[str] = _findall_prefixes(strings=moving_averages.columns.to_list())
    average_directional_index_windows: list[int] = [2**2, 2**4, 2**6, 2**8]
    for moving_average_prefix in moving_average_prefixes:
        for average_directional_index_window in average_directional_index_windows:
            moving_averages = _compute_average_directional_index(
                data=moving_averages,
                moving_average_prefix=moving_average_prefix,
                average_directional_index_window=average_directional_index_window,
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
    average_directional_indexes: DataFrame = moving_averages.copy(deep=True)
    adx_service.load_dataframe_as_parquet(dataframe=average_directional_indexes, filename=f"{uuid1()}.parquet")
    adx_service.delete_object()


# pylint: enable=duplicate-code
