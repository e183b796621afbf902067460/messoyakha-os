from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


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


class _ResponseMetadataSchema(BaseModel):
    request_id: str = Field(alias="RequestId")
    host_id: str = Field(alias="HostId")

    http_status_code: int = Field(alias="HTTPStatusCode")
    http_headers: _HTTPHeadersListObjectsResponseSchema = Field(alias="HTTPHeaders")

    retry_attempts: int = Field(alias="RetryAttempts")


class ContentSchema(BaseModel):
    key: Path = Field(alias="Key")
    e_tag: str = Field(alias="ETag")

    size: int = Field(alias="Size")
    storage_class: str = Field(alias="StorageClass")

    last_modified: datetime = Field(alias="LastModified")


class ListObjectsResponseSchema(BaseModel):
    name: str = Field(alias="Name")
    prefix: str = Field(alias="Prefix")

    response_metadata: _ResponseMetadataSchema = Field(alias="ResponseMetadata")
    is_truncated: bool = Field(alias="IsTruncated")

    contents: list[ContentSchema] = Field(alias="Contents")
    max_keys: int = Field(alias="MaxKeys")
    encoding_type: str = Field(alias="EncodingType")
    key_count: int = Field(alias="KeyCount")
