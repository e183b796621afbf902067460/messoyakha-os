from attr import define

from messoyakha_sdk.adapters.repositories.s3 import S3PolarsRepositoryBase


@define(slots=False, auto_attribs=True, kw_only=True)
class DohodS3Repository(S3PolarsRepositoryBase): ...
