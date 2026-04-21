from abc import ABC
from collections.abc import Callable
from functools import wraps
from http import HTTPMethod

from attrs import define, field
from httpx import URL, AsyncClient, Response


def route(endpoint: str) -> Callable[[Callable], Callable]:
	def decorator(func: Callable) -> Callable:
		@wraps(func)
		async def wrapper(self, *args, **kwargs):  # type: ignore[method-assign]  # noqa: ANN001, ANN202
			return await func(self, *args, endpoint=endpoint, **kwargs)

		return wrapper

	return decorator


@define(slots=False, auto_attribs=True, kw_only=True)
class HTTPAPIClientBase(ABC):
	_session: AsyncClient = field(init=False)

	async def __request(
		self,
		method: str,
		endpoint: str,
		parameters: dict | None = None,
		json: dict[str, str] | None = None,
		headers: dict[str, str] | None = None,
	) -> Response:
		url: URL = self._session.base_url.join(url=endpoint)
		response: Response = await self._session.request(
			method=method, url=url, params=parameters, json=json, headers=headers
		)
		response.raise_for_status()
		return response

	async def _get(
		self, endpoint: str, parameters: dict | None = None, headers: dict[str, str] | None = None
	) -> Response:
		return await self.__request(method=HTTPMethod.GET, endpoint=endpoint, parameters=parameters, headers=headers)

	async def _post(
		self,
		endpoint: str,
		parameters: dict | None = None,
		json: dict[str, str] | None = None,
		headers: dict[str, str] | None = None,
	) -> Response:
		return await self.__request(
			method=HTTPMethod.POST, endpoint=endpoint, parameters=parameters, json=json, headers=headers
		)
