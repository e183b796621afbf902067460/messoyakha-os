from functools import partial
from typing import TypeAlias

from attrs import define, field
from httpx import AsyncClient, Response

from messoyakha_finam_sdk.schemas.bars import (
    FinamBarsContextSchema,
    FinamBarsHeadersSchema,
    FinamBarsHTTPEndpointSchema,
    FinamBarsOutputSchema,
    FinamBarsParametersSchema,
)
from messoyakha_finam_sdk.schemas.clock import FinamClockHeadersSchema
from messoyakha_finam_sdk.schemas.sessions import FinamSessionsJsonSchema, FinamSessionsOutputSchema
from messoyakha_sdk.adapters.clients.http import HTTPAPIClientBase
from messoyakha_sdk.decorators.route import endpoint_route


@define(slots=False, auto_attribs=True, kw_only=True)
class _FinamAPIClientBase(HTTPAPIClientBase):
    _session: AsyncClient = field(
        init=False, factory=partial(AsyncClient, base_url="https://api.finam.ru", timeout=10, http2=True)
    )

    @endpoint_route("/v1/assets/clock")
    async def clock(self, headers_schema: FinamClockHeadersSchema, **kwargs) -> None:
        await self._get(headers=headers_schema.model_dump(by_alias=True), **kwargs)

    @endpoint_route("/v1/sessions")
    async def sessions(self, json_schema: FinamSessionsJsonSchema, **kwargs) -> FinamSessionsOutputSchema:
        response: Response = await self._post(json=json_schema.model_dump(), **kwargs)
        return FinamSessionsOutputSchema(**response.json())

    async def _bars(
        self,
        endpoint_schema: FinamBarsHTTPEndpointSchema,
        parameters_schema: FinamBarsParametersSchema,
        headers_schema: FinamBarsHeadersSchema,
        **kwargs,
    ) -> list[FinamBarsOutputSchema]:
        response: Response = await self._get(
            parameters=parameters_schema.model_dump(by_alias=True),
            headers=headers_schema.model_dump(by_alias=True),
            **kwargs,
        )
        context: FinamBarsContextSchema = FinamBarsContextSchema(
            ticker=endpoint_schema.ticker,
            venue=parameters_schema.venue,
            currency=parameters_schema.currency,
            product=parameters_schema.product,
            interval=parameters_schema.interval,
        )
        return [
            FinamBarsOutputSchema.model_validate(bar, context=context.model_dump()) for bar in response.json()["bars"]
        ]


@define(slots=False, auto_attribs=True, kw_only=True)
class FinamMISXSpotAPIClient(_FinamAPIClientBase):
    @endpoint_route("/v1/instruments/{symbol}/bars")
    async def bars(
        self,
        endpoint_schema: FinamBarsHTTPEndpointSchema,
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


@define(slots=False, auto_attribs=True, kw_only=True)
class FinamMISXFuturesAPIClient(_FinamAPIClientBase):
    @endpoint_route("/v1/instruments/{symbol}/bars")
    async def bars(
        self,
        endpoint_schema: FinamBarsHTTPEndpointSchema,
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


FinamAPIClient: TypeAlias = FinamMISXSpotAPIClient | FinamMISXFuturesAPIClient
