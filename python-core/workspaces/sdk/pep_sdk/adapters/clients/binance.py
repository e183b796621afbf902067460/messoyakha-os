from functools import partial
from typing import TypeAlias

from attrs import define, field
from httpx import AsyncClient, Response

from pep_sdk.adapters.clients._common.http import HTTPAPIClientBase
from pep_sdk.route import route
from pep_sdk.schemas.clients.binance import (
    BinanceKlinesContextSchema,
    BinanceKlinesOutputSchema,
    BinanceKlinesParametersSchema,
)


@define(slots=False, auto_attribs=True, kw_only=True)
class _BinanceAPIClientBase(HTTPAPIClientBase):
    async def _ping(self, **kwargs) -> None:
        await self._get(**kwargs)

    async def _klines(
        self, parameters_schema: BinanceKlinesParametersSchema, **kwargs
    ) -> list[BinanceKlinesOutputSchema]:
        response: Response = await self._get(parameters=parameters_schema.model_dump(by_alias=True), **kwargs)
        context: BinanceKlinesContextSchema = BinanceKlinesContextSchema(
            ticker=parameters_schema.ticker,
            market=parameters_schema.market,
            interval=parameters_schema.interval,
        )
        return [
            BinanceKlinesOutputSchema.model_validate(kline, context=context.model_dump()) for kline in response.json()
        ]


@define(slots=False, auto_attribs=True, kw_only=True)
class BinanceSpotAPIClient(_BinanceAPIClientBase):
    _session: AsyncClient = field(
        init=False, factory=partial(AsyncClient, base_url="https://api.binance.com", timeout=10, http2=True)
    )

    @route("/api/v3/ping")
    async def ping(self, **kwargs) -> None:
        await super()._ping(**kwargs)

    @route("/api/v3/klines")
    async def klines(
        self, parameters_schema: BinanceKlinesParametersSchema, **kwargs
    ) -> list[BinanceKlinesOutputSchema]:
        return await super()._klines(parameters_schema=parameters_schema, **kwargs)


@define(slots=False, auto_attribs=True, kw_only=True)
class BinanceUSDTMAPIClient(_BinanceAPIClientBase):
    _session: AsyncClient = field(
        init=False, factory=partial(AsyncClient, base_url="https://fapi.binance.com", timeout=10, http2=True)
    )

    @route("/fapi/v1/ping")
    async def ping(self, **kwargs) -> None:
        await super()._ping(**kwargs)

    @route("/fapi/v1/klines")
    async def klines(
        self, parameters_schema: BinanceKlinesParametersSchema, **kwargs
    ) -> list[BinanceKlinesOutputSchema]:
        return await super()._klines(parameters_schema=parameters_schema, **kwargs)


BinanceAPIClient: TypeAlias = BinanceSpotAPIClient | BinanceUSDTMAPIClient
