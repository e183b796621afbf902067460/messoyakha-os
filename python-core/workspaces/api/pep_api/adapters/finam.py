from functools import partial
from typing import TypeAlias

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
    async def _clock(self, headers_schema: FinamClockHeadersSchema, **kwargs) -> None:
        await self._get(headers=headers_schema.model_dump(by_alias=True), **kwargs)

    async def _sessions(self, json_schema: FinamSessionsJsonSchema, **kwargs) -> FinamSessionsOutputSchema:
        response: Response = await self._post(json=json_schema.model_dump(), **kwargs)
        return FinamSessionsOutputSchema(**response.json())

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


@define(slots=False, auto_attribs=True, kw_only=True)
class FinamMISXAPIClient(_FinamAPIClientBase):
    _session: AsyncClient = field(
        init=False, factory=partial(AsyncClient, base_url="https://api.finam.ru", timeout=10, http2=True)
    )

    @route("/v1/assets/clock")
    async def clock(self, headers_schema: FinamClockHeadersSchema, **kwargs) -> None:
        await super()._clock(headers_schema=headers_schema, **kwargs)

    @route("/v1/sessions")
    async def sessions(self, json_schema: FinamSessionsJsonSchema, **kwargs) -> FinamSessionsOutputSchema:
        return await super()._sessions(json_schema=json_schema, **kwargs)

    @route("/v1/instruments/{symbol}/bars")
    async def bars(
        self,
        endpoint_schema: FinamBarsEndpointSchema,
        parameters_schema: FinamBarsParametersSchema,
        headers_schema: FinamBarsHeadersSchema,
        **kwargs,
    ) -> list[FinamBarsOutputSchema]:
        return await super()._bars(
            endpoint_schema=endpoint_schema,
            parameters_schema=parameters_schema,
            headers_schema=headers_schema,
            **kwargs,
        )


FinamAPIClient: TypeAlias = FinamMISXAPIClient
