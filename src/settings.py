from datetime import datetime

from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):

    APP_NAME: str = "candlesticks-pipelines"
    APP_VERSION: str = "v0.0.1-alpha"

    S3_ACCESS_KEY_ID: str
    S3_SECRET_ACCESS_KEY: str
    S3_ENDPOINT_URL: HttpUrl = HttpUrl("https://s3.twcstorage.ru")
    S3_REGION_NAME: str = "ru-1"
    S3_CLIENT_READ_TIMEOUT: int = 5 * 60
    S3_CONNECT_TIMEOUT: int = 2 * 60
    S3_BUCKET: str = "f8e90488-f511555d-274b-4258-bffc-572dd1900382"

    EXCHANGE: str = "Binance"
    SECTION: str = "SPOT"
    TICKER: str = "BTCUSDT"
    INTERVAL: str = "4h"

    TRIGGER_DATE: datetime = datetime.now()

    MILLISECONDS_IN_SECOND: int = 10**3
    DAYS_IN_YEAR: int = 365

    class Config:
        case_sensitive = True


settings: AppSettings = AppSettings()
