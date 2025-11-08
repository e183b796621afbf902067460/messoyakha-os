# pylint: disable=duplicate-code
from uuid import uuid1
from warnings import filterwarnings

from boto3 import Session
from duckdb import DuckDBPyConnection
from pandas import DataFrame, Series

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.indicators import ADXRepository, AroonRepository, BinariesRepository, MARepository
from src.entrypoints.commmon.base import findall_prefixes
from src.schemas.filters import (
    ADXPathParametersSchema,
    ADXQueryParametersSchema,
    AroonPathParametersSchema,
    AroonQueryParametersSchema,
    BinaryPathParametersSchema,
    BinaryQueryParametersSchema,
    MAPathParametersSchema,
    MAQueryParametersSchema,
)
from src.services.domain.s3 import ADXService, AroonService, BinaryService, MAService
from src.settings import settings

filterwarnings("ignore")


# pylint: disable=redefined-outer-name,disallowed-name
def _compute_binary(data: DataFrame, a: str, b: str) -> DataFrame:  # noqa: WPS111
    prefix: str = f"is_{a}_greater_or_equal_than_{b}"
    data[prefix] = Series(data[a] >= data[b]).astype(int)
    return data


# pylint: enable=redefined-outer-name,disallowed-name


# pylint: disable=too-complex
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
    aroon_service: AroonService = AroonService(
        s3_client=s3_client,
        repository=AroonRepository(connection=duckdb_connection),
        query_parameters=AroonQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=AroonPathParametersSchema(bucket=settings.S3_BUCKET, directory="aroons"),
    )
    binary_service: BinaryService = BinaryService(
        s3_client=s3_client,
        repository=BinariesRepository(connection=duckdb_connection),
        query_parameters=BinaryQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=BinaryPathParametersSchema(bucket=settings.S3_BUCKET, directory="binaries"),
    )

    moving_averages: DataFrame | None = ma_service.extract_ma()
    if moving_averages is None:
        raise FileNotFoundError("There is no moving averages data.")
    moving_averages.drop_duplicates(inplace=True)
    moving_average_prefixes: list[str] = findall_prefixes(strings=moving_averages.columns.to_list())

    average_directional_indexes: DataFrame | None = adx_service.extract_adx()
    if average_directional_indexes is None:
        raise FileNotFoundError("There is no average directional indexes data.")
    average_directional_indexes.drop_duplicates(inplace=True)

    aroons: DataFrame | None = aroon_service.extract_aroon()
    if aroons is None:
        raise FileNotFoundError("There is no aroons data.")
    aroons.drop_duplicates(inplace=True)

    shifted_column: str

    moving_average_prefix: str
    for moving_average_prefix in moving_average_prefixes:
        moving_averages = _compute_binary(
            data=moving_averages, a=f"{moving_average_prefix}_close", b=f"{moving_average_prefix}_open"
        )
        moving_averages.drop(
            columns=[
                f"{moving_average_prefix}_open",
                f"{moving_average_prefix}_high",
                f"{moving_average_prefix}_low",
                f"{moving_average_prefix}_close",
            ],
            axis=1,
            inplace=True,
        )

    average_directional_index_column: str
    for average_directional_index_column in average_directional_indexes.columns.tolist():
        if average_directional_index_column.startswith("adx"):
            shifted_column = f"shifted_{average_directional_index_column}"
            average_directional_indexes[shifted_column] = average_directional_indexes[
                average_directional_index_column
            ].shift(1)
            average_directional_indexes = _compute_binary(
                data=average_directional_indexes, a=average_directional_index_column, b=shifted_column
            )
            average_directional_indexes.drop(
                columns=[average_directional_index_column, shifted_column], axis=1, inplace=True
            )

    aroon_column: str
    for aroon_column in aroons.columns.tolist():
        if aroon_column.startswith("aroon"):
            shifted_column = f"shifted_{aroon_column}"
            aroons[shifted_column] = aroons[aroon_column].shift(1)
            aroons = _compute_binary(data=aroons, a=aroon_column, b=shifted_column)
            aroons.drop(columns=[aroon_column, shifted_column], axis=1, inplace=True)

    # TODO: aroons
    binaries: DataFrame = moving_averages.merge(
        right=average_directional_indexes, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )

    binary_service.load_dataframe_as_parquet(dataframe=binaries, filename=f"{uuid1()}.parquet")
    binary_service.delete_object()


# pylint: enable=duplicate-code,too-complex
