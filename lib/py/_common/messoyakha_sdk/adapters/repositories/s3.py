from abc import ABC

from attr import define, field
from polars import DataFrame, LazyFrame, SQLContext
from pyarrow.fs import FSSpecHandler, PyFileSystem
from s3fs import S3FileSystem

from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema


@define(slots=False, auto_attribs=True, kw_only=True)
class S3PolarsRepositoryBase(ABC):
    _options: S3StorageOptionsSchema
    _context: SQLContext = field(init=False, factory=SQLContext)

    def __attrs_post_init__(self) -> None:
        self._fs: PyFileSystem = PyFileSystem(
            FSSpecHandler(
                S3FileSystem(
                    key=self._options.access_key,
                    secret=self._options.secret_key,
                    client_kwargs={
                        "endpoint_url": self._options.endpoint.unicode_string(),
                        "region_name": self._options.region,
                        "verify": False,
                    },
                )
            )
        )

    def _query(self, query: str) -> LazyFrame:
        return self._context.execute(query=query, eager=False)

    def _write(self, data: DataFrame, path: str, partition_columns: list[str] | None = None) -> None:
        data.write_parquet(
            file=path,
            pyarrow_options={
                "partition_cols": partition_columns,
                "filesystem": self._fs,
            },
            use_pyarrow=True,
        )
