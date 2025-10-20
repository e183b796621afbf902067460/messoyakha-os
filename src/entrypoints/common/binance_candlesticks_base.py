from datetime import datetime
from uuid import uuid1

from boto3 import Session
from duckdb import DuckDBPyConnection
from pandas import DataFrame, concat

from src.adapters.clients.binance import BinanceSpotAPIClient, BinanceUsdtmAPIClient
from src.adapters.clients.s3 import S3Client
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.common.duckdb_base import get_duckdb_connection
from src.schemas.domain.binance import BinanceKlinesInputSchema
from src.schemas.domain.s3 import ListObjectsResponseSchema
from src.schemas.queries import CandlesticksQueryParametersSchema, LatestTimestampQueryParametersSchema
from src.services.binance import BinanceService
from src.services.common.misc import determine_latest_timestamp, format_s3_key, format_s3_path
from src.settings import settings


# pylint: disable=too-many-locals, duplicate-code
async def main(client: BinanceSpotAPIClient | BinanceUsdtmAPIClient) -> None:
    await client.ping()

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
    binance_service: BinanceService = BinanceService(client=client)

    s3_path: str = format_s3_path(exchange=settings.EXCHANGE, section=settings.SECTION, directory="candlesticks")
    list_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="candlesticks"),
    )

    latest_timestamp: datetime | None = candlesticks_repository.query_latest_timestamp(
        parameters_schema=LatestTimestampQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path=f"{s3_path}/{list_objects_response.filename}" if list_objects_response.filename else f"{s3_path}/",
    )
    latest_timestamp = determine_latest_timestamp(latest_timestamp=latest_timestamp)

    existing_candlesticks: DataFrame | None = candlesticks_repository.query_candlesticks(
        parameters_schema=CandlesticksQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path=f"{s3_path}/{list_objects_response.filename}" if list_objects_response.filename else f"{s3_path}/",
    )

    incoming_candlesticks: DataFrame = await binance_service.get_klines(
        input_schema=BinanceKlinesInputSchema(
            ticker=settings.TICKER,
            section=settings.SECTION,
            interval=settings.INTERVAL,
            start_time=latest_timestamp,
            end_time=settings.TRIGGER_DATE,
        )
    )
    candlesticks: DataFrame = (
        concat([existing_candlesticks, incoming_candlesticks])
        if isinstance(existing_candlesticks, DataFrame)
        else incoming_candlesticks
    )
    candlesticks.drop_duplicates(inplace=True)
    candlesticks["exchange"] = settings.EXCHANGE

    candlesticks_repository.insert_dataframe_as_parquet(dataframe=candlesticks, key=f"{s3_path}/{uuid1()}.parquet")
    if list_objects_response.filename:
        s3_client.delete_object(
            bucket=settings.S3_BUCKET,
            key=format_s3_key(
                exchange=settings.EXCHANGE,
                section=settings.SECTION,
                directory="candlesticks",
                filename=list_objects_response.filename,
            ),
        )


# pylint: enable=too-many-locals, duplicate-code
