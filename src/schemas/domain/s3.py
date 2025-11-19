from ast import literal_eval
from datetime import datetime
from pathlib import Path
from typing import Any

from botocore.response import StreamingBody
from pydantic import BaseModel, Field, field_validator


class _HTTPHeadersBaseSchema(BaseModel):
    server: str
    connection: str

    content_type: str = Field(alias="content-type")

    x_amz_request_id: str = Field(alias="x-amz-request-id")
    x_robots_tag: str = Field(alias="x-robots-tag")

    date: str


class _HTTPHeadersListObjectsResponseSchema(_HTTPHeadersBaseSchema):
    transfer_encoding: str = Field(alias="transfer-encoding")

    vary: str


class _HTTPHeadersGetObjectResponseSchema(_HTTPHeadersBaseSchema):
    """HTTP header for get object S3 method."""


class _ResponseMetadataSchema(BaseModel):
    request_id: str = Field(alias="RequestId")
    host_id: str = Field(alias="HostId")

    http_status_code: int = Field(alias="HTTPStatusCode")
    http_headers: _HTTPHeadersListObjectsResponseSchema | _HTTPHeadersGetObjectResponseSchema = Field(
        alias="HTTPHeaders"
    )

    retry_attempts: int = Field(alias="RetryAttempts")


class _ContentSchema(BaseModel):
    key: Path = Field(alias="Key")
    e_tag: str = Field(alias="ETag")

    size: int = Field(alias="Size")
    storage_class: str = Field(alias="StorageClass")

    last_modified: datetime = Field(alias="LastModified")


class ListObjectsResponseSchema(BaseModel):
    name: str = Field(alias="Name")
    prefix: Path = Field(alias="Prefix")

    response_metadata: _ResponseMetadataSchema = Field(alias="ResponseMetadata")
    is_truncated: bool = Field(alias="IsTruncated")

    contents: list[_ContentSchema] = Field(alias="Contents", default=[])
    max_keys: int = Field(alias="MaxKeys")
    encoding_type: str = Field(alias="EncodingType")
    key_count: int = Field(alias="KeyCount")

    # pylint: disable=no-member
    @property
    def filepath(self) -> str:
        return self.prefix.as_posix()

    # pylint: enable=no-member

    @property
    def filename(self) -> str | None:
        filename: str | None = None

        contents: list[_ContentSchema] = [content for content in self.contents if content.size]
        if contents:
            assert len(contents) == 1  # noqa: S101
            filename = contents[0].key.name
        return filename


class GetObjectResponseSchema(BaseModel):
    body: StreamingBody = Field(alias="Body")
    metadata: dict[str, Any] = Field(alias="Metadata")
    response_metadata: _ResponseMetadataSchema = Field(alias="ResponseMetadata")

    @field_validator("metadata", mode="after")  # type: ignore[misc]
    @classmethod
    def eval_metadata(cls, metadata: dict[str, Any]) -> dict[str, Any]:
        return {key: literal_eval(node_or_string=value) for key, value in metadata.items()}

    class Config:
        arbitrary_types_allowed = True
