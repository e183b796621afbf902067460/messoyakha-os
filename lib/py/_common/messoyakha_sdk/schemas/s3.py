from pydantic import BaseModel, Field, HttpUrl, computed_field


class S3StorageOptionsSchema(BaseModel):
    access_key: str = Field(serialization_alias="aws_access_key_id")
    secret_key: str = Field(serialization_alias="aws_secret_access_key")
    region: str = Field(serialization_alias="aws_region")
    endpoint: HttpUrl = Field(exclude=True)

    @computed_field(alias="aws_endpoint_url")
    def _endpoint(self) -> str:
        return self.endpoint.unicode_string()
