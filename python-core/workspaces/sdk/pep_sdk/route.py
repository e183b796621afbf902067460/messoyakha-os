from collections.abc import Callable
from functools import wraps

from pep_sdk.schemas.common.endpoints import EndpointSchemaBase


def route(endpoint: str) -> Callable[[Callable], Callable]:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, endpoint=endpoint, **kwargs):  # type: ignore[method-assign]  # noqa: ANN001, ANN202
            for key, value in kwargs.items():
                if issubclass(type(value), EndpointSchemaBase) and (endpoint_schema := kwargs.get(key)):
                    endpoint = endpoint.format(**endpoint_schema.model_dump(by_alias=True))
                    break
            return await func(self, *args, endpoint=endpoint, **kwargs)

        return wrapper

    return decorator
