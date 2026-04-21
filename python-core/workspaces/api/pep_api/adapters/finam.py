from functools import partial

from attrs import define, field
from httpx import AsyncClient

from pep_api.adapters.common.http import HTTPAPIClientBase, route


@define(slots=False, auto_attribs=True, kw_only=True)
class FinamAPIClient(HTTPAPIClientBase):
	_session: AsyncClient = field(init=False, factory=partial(AsyncClient, base_url="https://api.finam.ru", http2=True))

	@route("/v1/sessions")
	async def sessions(self, json_schema: ..., **kwargs) -> None:
		await self._post(json=..., **kwargs)
