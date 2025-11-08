# pylint: disable=duplicate-code
from uuid import uuid1
from warnings import filterwarnings

from boto3 import Session
from duckdb import DuckDBPyConnection
from pandas import DataFrame

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.indicators import BinariesRepository, StreaksRepository
from src.schemas.filters import (
    BinaryPathParametersSchema,
    BinaryQueryParametersSchema,
    StreakPathParametersSchema,
    StreakQueryParametersSchema,
)
from src.services.domain.s3 import BinaryService, StreakService
from src.settings import settings

filterwarnings("ignore")

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

    binary_service: BinaryService = BinaryService(
        s3_client=s3_client,
        repository=BinariesRepository(connection=duckdb_connection),
        query_parameters=BinaryQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=BinaryPathParametersSchema(bucket=settings.S3_BUCKET, directory="binaries"),
    )
    streak_service: StreakService = StreakService(
        s3_client=s3_client,
        repository=StreaksRepository(connection=duckdb_connection),
        query_parameters=StreakQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=StreakPathParametersSchema(bucket=settings.S3_BUCKET, directory="streaks"),
    )

    binaries: DataFrame | None = binary_service.extract_binary()
    if binaries is None:
        raise FileNotFoundError("There is no binaries data.")
    binaries.drop_duplicates(inplace=True)

    binary_column: str
    for binary_column in binaries.columns.tolist():
        if binary_column.startswith("is"):
            prefix: str = f"streak_{binary_column}"
            binaries["streak_start"] = binaries[binary_column].ne(other=binaries[binary_column].shift(1))
            binaries["streak_id"] = binaries["streak_start"].cumsum()
            binaries[prefix] = binaries.groupby("streak_id").cumcount() + 1

            binaries.drop(columns=[binary_column, "streak_start", "streak_id"], axis=1, inplace=True)

    streaks: DataFrame = binaries.copy(deep=True)
    streak_service.load_dataframe_as_parquet(dataframe=streaks, filename=f"{uuid1()}.parquet")
    streak_service.delete_object()


# pylint: enable=duplicate-code,too-complex
