from collections.abc import Callable
from typing import Protocol, runtime_checkable
from functools import wraps

from pydantic import BaseModel


@runtime_checkable
class _HTTPEndpointProtocol(Protocol):
    def cohere_http_endpoint(self) -> None:
        pass


def route(endpoint: str) -> Callable[[Callable], Callable]:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, endpoint=endpoint, **kwargs):  # type: ignore[method-assign]  # noqa: ANN001, ANN202
            for key, value in kwargs.items():
                if isinstance(value, _HTTPEndpointProtocol) and issubclass(value, BaseModel):
                    endpoint: str = endpoint.format(**value.model_dump(by_alias=True))
                    break
            return await func(self, *args, endpoint=endpoint, **kwargs)

        return wrapper

    return decorator
