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


class IcebergSettingsBase(S3SettingsBase):
    NAMESPACE: str = Field(validation_alias="ICEBERG_CATALOG", default="default")

    TYPE_CATALOG_PROPERTY: str = Field(validation_alias="ICEBERG_TYPE_CATALOG_PROPERTY", default="sql")
    PATH_CATALOG_PROPERTY: str = Field(validation_alias="ICEBERG_WAREHOUSE_CATALOG_PROPERTY", default="/")
    URI_CATALOG_PROPERTY: AnyUrl = Field(
        validation_alias="ICEBERG_URI_CATALOG_PROPERTY", default=AnyUrl("sqlite:///iceberg-metadata.db")
    )

    @cached_property
    def catalog(self) -> Catalog:
        return load_catalog(name=self.NAMESPACE, **self.iceberg_properties_dump())

    @property
    def s3_normalized_path(self) -> str:
        return f"s3://{self.BUCKET}"

    def iceberg_properties_dump(self) -> dict[str, str]:
        return {
            "type": self.TYPE_CATALOG_PROPERTY,
            "warehouse": f"{self.s3_normalized_path}{self.PATH_CATALOG_PROPERTY}",
            "uri": self.URI_CATALOG_PROPERTY.encoded_string(),
            "s3.endpoint": self.ENDPOINT.encoded_string(),
            "s3.access-key-id": self.ACCESS_KEY,
            "s3.secret-access-key": self.SECRET_KEY,
        }
