from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings


class IcebergSettingsBase(BaseSettings):
    URI: AnyUrl = Field(validation_alias="ICEBERG_METADATA_DSN", default=AnyUrl("sqlite:///iceberg-metadata.db"))
