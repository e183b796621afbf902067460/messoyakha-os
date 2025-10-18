from attr import attr, attrs
from boto3 import Session
from botocore.client import BaseClient
from botocore.config import Config

from src.schemas.domain.s3 import ListObjectsResponseSchema
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

    def delete_object(self, bucket: str, key: str) -> None:
        self._client.delete_object(Bucket=bucket, Key=key)

    _client: BaseClient = attr(init=False)
