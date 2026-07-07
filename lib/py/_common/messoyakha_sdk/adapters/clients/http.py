from abc import ABC
from http import HTTPMethod

from attrs import define, field
from httpx import URL, AsyncClient, Response


@define(slots=False, auto_attribs=True, kw_only=True)
class HTTPAPIClientBase(ABC):
    _session: AsyncClient = field(init=False)

    async def _request(
        self,
        method: str,
        endpoint: str | None = None,
        parameters: dict | None = None,
        data: dict[str, str] | None = None,
        json: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        url: URL = self._session.base_url.join(url=endpoint) if endpoint else self._session.base_url
        response: Response = await self._session.request(
            method=method, url=url, params=parameters, data=data, json=json, headers=headers
        )
        response.raise_for_status()
        return response

    async def _get(
        self, endpoint: str | None = None, parameters: dict | None = None, headers: dict[str, str] | None = None
    ) -> Response:
        return await self._request(method=HTTPMethod.GET, endpoint=endpoint, parameters=parameters, headers=headers)

    async def _post(
        self,
        endpoint: str | None = None,
        parameters: dict | None = None,
        data: dict[str, str] | None = None,
        json: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        return await self._request(
            method=HTTPMethod.POST, endpoint=endpoint, parameters=parameters, data=data, json=json, headers=headers
        )
