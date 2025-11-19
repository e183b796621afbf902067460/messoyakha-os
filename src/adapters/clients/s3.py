from typing import Any

from attr import attr, attrs
from boto3 import Session
from botocore.client import BaseClient
from botocore.config import Config

from src.schemas.domain.s3 import GetObjectResponseSchema, ListObjectsResponseSchema
from src.settings import settings

_CLIENT_CONFIG: Config = Config(
    read_timeout=settings.S3_CLIENT_READ_TIMEOUT, connect_timeout=settings.S3_CONNECT_TIMEOUT
)


@attrs(slots=True, auto_attribs=True, kw_only=True)
class S3Client:

    _session: Session

    def __attrs_post_init__(self) -> None:
        self._client = self._session.client(
            service_name="s3", endpoint_url=settings.S3_ENDPOINT_URL.encoded_string(), config=_CLIENT_CONFIG
        )

    def list_objects(self, bucket: str, prefix: str) -> ListObjectsResponseSchema:
        list_objects_response_schema: ListObjectsResponseSchema = ListObjectsResponseSchema(
            **self._client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        )
        return list_objects_response_schema

    def get_object(self, bucket: str, key: str) -> GetObjectResponseSchema:
        get_object_response_schema: GetObjectResponseSchema = GetObjectResponseSchema(
            **self._client.get_object(Bucket=bucket, Key=key)
        )
        return get_object_response_schema

    def put_object(self, data: bytes, metadata: dict[str, Any], bucket: str, key: str) -> None:
        self._client.put_object(Bucket=bucket, Key=key, Body=data, Metadata=metadata)

    def delete_object(self, bucket: str, key: str) -> None:
        self._client.delete_object(Bucket=bucket, Key=key)

    _client: BaseClient = attr(init=False)
