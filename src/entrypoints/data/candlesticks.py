from asyncio import run
from datetime import datetime, timedelta
from uuid import uuid1

from boto3 import Session
from httpx import AsyncClient as HTTPAsyncClient
from httpx import AsyncHTTPTransport
from pandas import DataFrame, concat

from src.adapters.clients.binance import BinanceSpotAPIClient
from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.schemas.domain.binance import BinanceKlinesInputSchema
from src.schemas.filters import (
    LatestTimestampPathParametersSchema,
    LatestTimestampQueryParametersSchema,
    OHLCPathParametersSchema,
    OHLCQueryParametersSchema,
)
from src.services.common.api_base import APIBaseService
from src.services.domain.binance import BinanceService
from src.services.domain.s3 import OHLCService
from src.settings import settings

_YEARS_IN_RETROSPECTIVE: int = settings.TRIGGER_DATE.year - 2010  # noqa: WPS432


def _determine_latest_timestamp(latest_timestamp: datetime | None) -> datetime:
    if latest_timestamp is None:
        return settings.TRIGGER_DATE - timedelta(days=settings.DAYS_IN_YEAR * _YEARS_IN_RETROSPECTIVE)
    return latest_timestamp + timedelta(seconds=1)


# pylint: disable=too-many-locals, duplicate-code, redefined-outer-name
async def main(service: APIBaseService) -> None:
    latest_timestamp_query_parameters: LatestTimestampQueryParametersSchema = LatestTimestampQueryParametersSchema(
        ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
    )
    ohlc_query_parameters: OHLCQueryParametersSchema = OHLCQueryParametersSchema(
        ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
    )
    latest_timestamp_path_parameters: LatestTimestampPathParametersSchema = LatestTimestampPathParametersSchema(
        bucket=settings.S3_BUCKET
    )
    ohlc_path_parameters: OHLCPathParametersSchema = OHLCPathParametersSchema(bucket=settings.S3_BUCKET)

    ohlc_service: OHLCService = OHLCService(
        s3_client=S3Client(
            session=Session(
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                region_name=settings.S3_REGION_NAME,
            )
        ),
        repository=CandlesticksRepository(
            connection=get_duckdb_connection(
                s3_access_key_id=settings.S3_ACCESS_KEY_ID,
                s3_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                s3_endpoint_url=settings.S3_ENDPOINT_URL.host,
                s3_region_name=settings.S3_REGION_NAME,
            )
        ),
        query_parameters=latest_timestamp_query_parameters or ohlc_query_parameters,
        path_parameters=latest_timestamp_path_parameters or ohlc_path_parameters,
    )

    latest_timestamp = _determine_latest_timestamp(latest_timestamp=ohlc_service.latest_timestamp)
    incoming_candlesticks: DataFrame = await service.get_ohlc(
        input_schema=BinanceKlinesInputSchema(
            ticker=settings.TICKER,
            section=settings.SECTION,
            interval=settings.INTERVAL,
            start_time=latest_timestamp,
            end_time=settings.TRIGGER_DATE,
        )
    )
    candlesticks: DataFrame = (
        concat([ohlc_service.ohlc, incoming_candlesticks])
        if isinstance(ohlc_service.ohlc, DataFrame)
        else incoming_candlesticks
    )
    candlesticks.drop_duplicates(inplace=True)
    candlesticks["exchange"] = settings.EXCHANGE

    candlesticks.to_csv("candlesticks.csv", index=False)

    ohlc_service.load_ohlc(dataframe=candlesticks, filename=f"{uuid1()}.parquet")
    ohlc_service.delete_object()


# pylint: enable=too-many-locals, duplicate-code, redefined-outer-name


if __name__ == "__main__":
    client: BinanceSpotAPIClient = BinanceSpotAPIClient(
        session=HTTPAsyncClient(
            base_url="https://api.binance.com",
            timeout=60,
            transport=AsyncHTTPTransport(retries=3, http2=True),
            follow_redirects=True,
        )
    )
    service: BinanceService = BinanceService(client=client)
    run(main=main(service=service))
