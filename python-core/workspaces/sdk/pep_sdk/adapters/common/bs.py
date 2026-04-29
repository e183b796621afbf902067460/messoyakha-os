from abc import ABC
from http import HTTPMethod

from attrs import define, field
from crawlee import Request
from crawlee._types import HttpMethod as CrawleeHTTPMethodLiteral
from crawlee.storages import RequestQueue
from httpx import URL, AsyncClient


@define(slots=False, auto_attribs=True, kw_only=True)
class BSCrawlerBase(ABC):
    _session: AsyncClient = field(init=False)

    async def _request(
        self,
        method: CrawleeHTTPMethodLiteral,
        endpoint: str | None = None,
        payload: str | None = None,
        headers: dict[str, str] | None = None,
        label: str | None = None,
    ) -> None:
        url: URL = self._session.base_url.join(url=endpoint) if endpoint else self._session.base_url
        request: Request = Request.from_url(url=str(url), method=method, payload=payload, headers=headers, label=label)
        queue: RequestQueue = await RequestQueue.open()
        await queue.add_request(request=request)

    async def _get(
        self,
        endpoint: str | None = None,
        payload: str | None = None,
        headers: dict[str, str] | None = None,
        label: str | None = None,
    ) -> None:
        await self._request(
            method=HTTPMethod.GET.value,  # type: ignore[bad-argument-type]
            endpoint=endpoint,
            payload=payload,
            headers=headers,
            label=label,
        )
