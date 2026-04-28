from functools import partial

from attrs import define, field
from httpx import AsyncClient, Response

from pep_api.adapters.common.http import HTTPAPIClientBase, route
from pep_api.schemas.finam import (
    FinamBarsContextSchema,
    FinamBarsEndpointSchema,
    FinamBarsHeadersSchema,
    FinamBarsOutputSchema,
    FinamBarsParametersSchema,
    FinamClockHeadersSchema,
    FinamSessionsJsonSchema,
    FinamSessionsOutputSchema,
)


@define(slots=False, auto_attribs=True, kw_only=True)
class _FinamAPIClientBase(HTTPAPIClientBase):
    _session: AsyncClient = field(
        init=False, factory=partial(AsyncClient, base_url="https://api.finam.ru", timeout=10, http2=True)
    )

    @route("/v1/assets/clock")
    async def _clock(self, headers_schema: FinamClockHeadersSchema, **kwargs) -> None:
        await self._get(headers=headers_schema.model_dump(by_alias=True), **kwargs)

    @route("/v1/sessions")
    async def _sessions(self, json_schema: FinamSessionsJsonSchema, **kwargs) -> FinamSessionsOutputSchema:
        response: Response = await self._post(json=json_schema.model_dump(), **kwargs)
        return FinamSessionsOutputSchema(**response.json())

    @route("/v1/instruments/{symbol}/bars")
    async def _bars(
        self,
        endpoint_schema: FinamBarsEndpointSchema,
        parameters_schema: FinamBarsParametersSchema,
        headers_schema: FinamBarsHeadersSchema,
        **kwargs,
    ) -> list[FinamBarsOutputSchema]:
        response: Response = await self._get(
            parameters=parameters_schema.model_dump(by_alias=True),
            headers=headers_schema.model_dump(by_alias=True),
            **kwargs,
        )
        context_schema: FinamBarsContextSchema = FinamBarsContextSchema(
            ticker=endpoint_schema.ticker,
            market=endpoint_schema.market,
            interval=parameters_schema.interval,
        )
        return [
            FinamBarsOutputSchema.model_validate(bar, context=context_schema.model_dump())
            for bar in response.json()["bars"]
        ]
