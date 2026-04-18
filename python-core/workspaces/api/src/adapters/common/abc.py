from abc import ABC

from attr import attrs
from httpx import URL, AsyncClient, Response


@attrs(slots=True, auto_attribs=True, kw_only=True)
class APIClientBase(ABC):
	"""Base class for API clients with shared HTTP request logic."""

	_session: AsyncClient

	async def __request(
		self, method: str, endpoint: str, parameters: dict | None = None, headers: dict[str, str] | None = None
	) -> Response:
		url: URL = self._session.base_url.join(url=endpoint)
		response: Response = await self._session.request(method=method, url=url, params=parameters, headers=headers)
		response.raise_for_status()
		return response

	async def _get(
		self, endpoint: str, parameters: dict | None = None, headers: dict[str, str] | None = None
	) -> Response:
		return await self.__request(method="GET", endpoint=endpoint, parameters=parameters, headers=headers)
