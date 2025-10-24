from asyncio import run
from datetime import datetime
from typing import Literal
from uuid import uuid1

from attr import attrib, attrs
from boto3 import Session
from duckdb import DuckDBPyConnection
from httpx import AsyncClient as HTTPAsyncClient
from httpx import AsyncHTTPTransport
from pandas import DataFrame, concat

from src.adapters.clients.binance import BinanceSpotAPIClient, BinanceUsdtmAPIClient
from src.adapters.clients.s3 import S3Client
from src.adapters.repositories.common.duckdb_base import get_duckdb_connection
from src.adapters.repositories.ohlc import OHLCRepository
from src.schemas.domain.binance import BinanceKlinesInputSchema
from src.schemas.domain.s3 import ListObjectsResponseSchema
from src.schemas.queries import LatestTimestampQueryParametersSchema, OHLCQueryParametersSchema
from src.services.binance import BinanceService
from src.services.common.misc import determine_latest_timestamp, format_s3_key, format_s3_path
from src.settings import settings

_SPOT_BINANCE_SECTION: Literal["SPOT"] = "SPOT"
_USDTM_BINANCE_SECTION: Literal["USDT-M"] = "USDT-M"


# pylint: disable=too-many-locals, duplicate-code
async def _main(client: BinanceSpotAPIClient | BinanceUsdtmAPIClient) -> None:
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
    ohlc_repository: OHLCRepository = OHLCRepository(connection=duckdb_connection)
    binance_service: BinanceService = BinanceService(client=client)

    s3_path: str = format_s3_path(exchange=settings.EXCHANGE, section=settings.SECTION, directory="candlesticks")
    list_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="candlesticks"),
    )

    latest_timestamp: datetime | None = ohlc_repository.query_latest_timestamp(
        parameters_schema=LatestTimestampQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path=f"{s3_path}/{list_objects_response.filename}" if list_objects_response.filename else f"{s3_path}/",
    )
    latest_timestamp = determine_latest_timestamp(latest_timestamp=latest_timestamp)

    existing_candlesticks: DataFrame | None = ohlc_repository.query_candlesticks(
        parameters_schema=OHLCQueryParametersSchema(
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

    ohlc_repository.insert_dataframe_as_parquet(dataframe=candlesticks, key=f"{s3_path}/{uuid1()}.parquet")
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


@attrs(slots=True, auto_attribs=True, kw_only=True)
class _BinanceAPIClientFactory:
    _factory: dict[str, BinanceSpotAPIClient | BinanceUsdtmAPIClient] = attrib(init=False, default={})

    def _add_binance_api_client(
        self, binance_section: str, binance_api_client: BinanceSpotAPIClient | BinanceUsdtmAPIClient
    ) -> None:
        self._factory[binance_section] = binance_api_client

    def __attrs_post_init__(self) -> None:
        self._add_binance_api_client(
            binance_section=_SPOT_BINANCE_SECTION,
            binance_api_client=BinanceSpotAPIClient(
                session=HTTPAsyncClient(
                    base_url="https://api.binance.com",
                    timeout=60,
                    transport=AsyncHTTPTransport(retries=3, http2=True),
                    follow_redirects=True,
                )
            ),
        )
        self._add_binance_api_client(
            binance_section=_USDTM_BINANCE_SECTION,
            binance_api_client=BinanceUsdtmAPIClient(
                session=HTTPAsyncClient(
                    base_url="https://fapi.binance.com",
                    timeout=60,
                    transport=AsyncHTTPTransport(retries=3, http2=True),
                    follow_redirects=True,
                )
            ),
        )

    def get_binance_api_client(self, binance_section: str) -> BinanceSpotAPIClient | BinanceUsdtmAPIClient:
        return self._factory.get(binance_section)


if __name__ == "__main__":
    binance_api_client_factory: _BinanceAPIClientFactory = _BinanceAPIClientFactory()
    run(main=_main(client=binance_api_client_factory.get_binance_api_client(binance_section=settings.SECTION)))
