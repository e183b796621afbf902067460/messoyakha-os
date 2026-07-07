from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from loguru import logger
from polars import scan_parquet
from pydantic import BaseModel

from messoyakha_sdk.typings import T


if TYPE_CHECKING:
    from messoyakha_sdk.adapters.clients.http import HTTPAPIClientBase
    from messoyakha_sdk.adapters.clients.web import CrawleeWebClientBase
    from messoyakha_sdk.adapters.repositories.s3 import S3PolarsRepositoryBase


@runtime_checkable
class _HTTPEndpointProtocol(Protocol):
    def _cohere_http_endpoint(self) -> None:
        pass


@runtime_checkable
class _S3PathProtocol(Protocol):
    def _cohere_s3_path(self) -> None:
        pass


def endpoint_route(endpoint: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(self: HTTPAPIClientBase | CrawleeWebClientBase, *args, endpoint=endpoint, **kwargs) -> T:  # noqa: ANN001
            for value in kwargs.values():
                if isinstance(value, _HTTPEndpointProtocol) and isinstance(value, BaseModel):
                    endpoint: str = endpoint.format(**value.model_dump(by_alias=True))
                    break
            return await func(self, *args, endpoint=endpoint, **kwargs)

        return wrapper

    return decorator


def path_route(table: str, path: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(method: Callable[..., T]) -> Callable[..., T]:
        @wraps(method)
        def wrapper(self: S3PolarsRepositoryBase, *args, path=path, **kwargs) -> T:  # noqa: ANN001
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
