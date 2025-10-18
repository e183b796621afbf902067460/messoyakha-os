from abc import ABC
from typing import Literal

from attr import attrs
from httpx import URL, AsyncClient, Response

_GET: Literal["GET"] = "GET"


@attrs(slots=True, auto_attribs=True, kw_only=True)
class APIClientBase(ABC):

    _session: AsyncClient

    async def __request(self, method: str, endpoint: str, parameters: dict | None) -> Response | None:
        url: URL = self._session.base_url.join(url=endpoint)
        response: Response | None = None
        if method == _GET:
            response = await self._session.get(url=url, params=parameters)

        if response:
            response.raise_for_status()

        return response

    async def _get(self, endpoint: str, parameters: dict | None = None) -> Response | None:
        return await self.__request(method=_GET, endpoint=endpoint, parameters=parameters)
