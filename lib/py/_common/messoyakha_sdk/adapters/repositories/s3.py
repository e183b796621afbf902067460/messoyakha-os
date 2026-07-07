from abc import ABC
from collections.abc import Callable
from functools import wraps
from typing import Protocol, runtime_checkable

from attr import define, field
from polars import DataFrame, LazyFrame, SQLContext
from pyarrow.fs import FSSpecHandler, PyFileSystem
from pydantic import BaseModel
from s3fs import S3FileSystem


@runtime_checkable
class _S3PathProtocol(Protocol):
    def _cohere_s3_path(self) -> None:
        pass


def route(path: str) -> Callable[[Callable], Callable]:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, path=path, **kwargs):  # noqa: ANN001, ANN202
            for value in kwargs.values():
                if isinstance(value, _S3PathProtocol) and isinstance(value, BaseModel):
                    path: str = path.format(**value.model_dump(by_alias=True))
                    break
            return await func(self, *args, path=path, **kwargs)

        return wrapper

    return decorator


@define(slots=False, auto_attribs=True, kw_only=True)
class S3PolarsRepositoryBase(ABC):
    _options: dict[str, str]
    _context: SQLContext = field(init=False, factory=SQLContext)

    def __attrs_post_init__(self) -> None:
        self._fs: PyFileSystem = PyFileSystem(
            FSSpecHandler(
                S3FileSystem(
                    key=self._options["aws_access_key_id"],
                    secret=self._options["aws_secret_access_key"],
                    client_kwargs={
                        "endpoint_url": self._options["aws_endpoint_url"],
                        "region_name": self._options["aws_region"],
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
