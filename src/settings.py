from datetime import datetime

from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    APP_NAME: str = "candlesticks-pipelines"
    APP_VERSION: str = "v0.0.1-alpha"

    S3_ACCESS_KEY_ID: str = "PRQF3B2VHJ0N77L2XTUH"
    S3_SECRET_ACCESS_KEY: str = "HQBUH5l74bWvdGH8H5zhzOxfsfbUUEonIyrrN0T5"
    S3_ENDPOINT_URL: HttpUrl = HttpUrl("https://s3.twcstorage.ru")
    S3_REGION_NAME: str = "ru-1"
    S3_CLIENT_READ_TIMEOUT: int = 5 * 60
    S3_CONNECT_TIMEOUT: int = 2 * 60
    S3_BUCKET: str = "f8e90488-f511555d-274b-4258-bffc-572dd1900382"

    HYPERLIQUID_L1_ADDRESS: str = "0x8BD4B2312f6C95B0D40E7407b26b124B25cbA375"
    HYPERLIQUID_SECRET_KEY: str = "0x8f4d4485a80a5b2f13e6fc7480920c1f7ff4c753cf1c2b4fcf52eb2560b2d620"

    EXCHANGE: str = "Binance"
    SECTION: str = "SPOT"
    TICKER: str = "BTCUSDT"
    INTERVAL: str = "1w"

    TRIGGER_DATE: datetime = datetime.now()

    MILLISECONDS_IN_SECOND: int = 10**3
    DAYS_IN_YEAR: int = 365

    class Config:
        case_sensitive = True


settings: AppSettings = AppSettings()
