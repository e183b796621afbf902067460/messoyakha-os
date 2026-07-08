from functools import cached_property

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings

from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema


class S3SettingsBase(BaseSettings):
    ACCESS_KEY: str
    SECRET_KEY: str

    ENDPOINT: HttpUrl = Field(default=HttpUrl("https://s3.twcstorage.ru"))
    REGION: str = Field(default="ru-1")

    class Config:
        case_sensitive = True

    @cached_property
    def storage_options(self) -> S3StorageOptionsSchema:
        return S3StorageOptionsSchema(
            access_key=self.ACCESS_KEY, secret_key=self.SECRET_KEY, region=self.REGION, endpoint=self.ENDPOINT
        )
