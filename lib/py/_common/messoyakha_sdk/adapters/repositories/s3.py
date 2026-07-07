from abc import ABC
from collections.abc import Callable
from functools import wraps
from typing import Protocol, TypeVar, runtime_checkable

from attr import define, field
from loguru import logger
from polars import DataFrame, LazyFrame, SQLContext, scan_parquet
from pyarrow.fs import FSSpecHandler, PyFileSystem
from pydantic import BaseModel
from s3fs import S3FileSystem

from messoyakha_sdk.schemas.s3 import S3StorageOptionsSchema
from messoyakha_sdk.typings import T


_S3PolarsRepositoryBase = TypeVar("_S3PolarsRepositoryBase", bound="S3PolarsRepositoryBase")


@runtime_checkable
class _S3PathProtocol(Protocol):
    def _cohere_s3_path(self) -> None:
        pass


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


def route(table: str, path: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(method: Callable[..., T]) -> Callable[..., T]:
        @wraps(method)
        def wrapper(self: _S3PolarsRepositoryBase, *args, path=path, **kwargs) -> T:  # noqa: ANN001
            for value in kwargs.values():
                if isinstance(value, _S3PathProtocol) and isinstance(value, BaseModel):
                    path: str = path.format(**value.model_dump(by_alias=True))
                    break
            path = f"s3://{path}"
            logger.info(f"Querying {path}.")

            self._context.register(
                name=table,
                frame=scan_parquet(
                    source=path,
                    storage_options=self._options.model_dump(by_alias=True),
                    extra_columns="ignore",
                    allow_missing_columns=True,
                    hive_partitioning=True,
                ),
            )
            return method(self, *args, **kwargs)

        return wrapper

    return decorator
