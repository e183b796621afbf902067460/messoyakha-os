from functools import partial

from attrs import define, field
from httpx import AsyncClient, Response

from pep_api.adapters.common.http import HTTPAPIClientBase, route
from pep_api.schemas.finam import FinamSessionsJsonSchema, FinamSessionsOutputSchema


@define(slots=False, auto_attribs=True, kw_only=True)
class FinamAPIClient(HTTPAPIClientBase):
	_session: AsyncClient = field(init=False, factory=partial(AsyncClient, base_url="https://api.finam.ru", http2=True))

	@route("/v1/sessions")
	async def sessions(self, json_schema: FinamSessionsJsonSchema, **kwargs) -> FinamSessionsOutputSchema:
		response: Response = await self._post(json=json_schema.model_dump(), **kwargs)
		return FinamSessionsOutputSchema(**response.json())
