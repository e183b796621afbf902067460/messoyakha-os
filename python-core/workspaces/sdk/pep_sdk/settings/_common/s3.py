from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class S3SettingsBase(BaseSettings):
    ACCESS_KEY: str = Field(validation_alias="S3_ACCESS_KEY")
    SECRET_KEY: str = Field(validation_alias="S3_SECRET_KEY")

    BUCKET: str = Field(validation_alias="S3_BUCKET")

    ENDPOINT: HttpUrl = Field(validation_alias="S3_ENDPOINT", default=HttpUrl("https://s3.twcstorage.ru"))
    REGION: str = Field(validation_alias="S3_REGION", default="ru-1")

    class Config:
        case_sensitive = True
