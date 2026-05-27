from functools import cached_property

from pydantic import AnyUrl, Field, HttpUrl
from pydantic_settings import BaseSettings
from pyiceberg.catalog import Catalog, load_catalog


class S3SettingsBase(BaseSettings):
    ACCESS_KEY: str = Field(validation_alias="S3_ACCESS_KEY")
    SECRET_KEY: str = Field(validation_alias="S3_SECRET_KEY")

    BUCKET: str = Field(validation_alias="S3_BUCKET")

    ENDPOINT: HttpUrl = Field(validation_alias="S3_ENDPOINT", default=HttpUrl("https://s3.twcstorage.ru"))
    REGION: str = Field(validation_alias="S3_REGION", default="ru-1")

    class Config:
        case_sensitive = True

    @cached_property
    def uri(self) -> str:
        return f"s3://{self.BUCKET}"


class IcebergSettingsBase(S3SettingsBase):
    CATALOG: str = Field(validation_alias="ICEBERG_CATALOG", default="default")

    SQL_TYPE_PROPERTY: str = Field(validation_alias="ICEBERG_SQL_TYPE_PROPERTY", default="sql")
    SQL_URI_PROPERTY: AnyUrl = Field(
        validation_alias="ICEBERG_SQL_URI_PROPERTY", default=AnyUrl("sqlite:///iceberg-metadata.db")
    )

    @cached_property
    def catalog(self) -> Catalog:
        return load_catalog(
            name=self.CATALOG,
            **{
                "type": self.SQL_TYPE_PROPERTY,
                "warehouse": f"{self.uri}/",
                "uri": self.SQL_URI_PROPERTY.unicode_string(),
                "s3.region": self.REGION,
                "s3.endpoint": self.ENDPOINT.unicode_string(),
                "s3.access-key-id": self.ACCESS_KEY,
                "s3.secret-access-key": self.SECRET_KEY,
            },
        )
