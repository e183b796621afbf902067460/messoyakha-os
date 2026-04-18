from httpx import Response

from pep_api.adapters.common.abc import APIClientBase, route
from pep_api.schemas.binance import BinanceKlinesOutputSchema, BinanceKlinesParametersSchema


class BinanceAPIClientBase(APIClientBase):
	"""Binance API client base."""

	async def _ping(self, *args, **kwargs) -> None:
		"""Ping the API endpoint."""
		await self._get(*args, **kwargs)

	async def _klines(
		self, parameters_schema: BinanceKlinesParametersSchema, **kwargs
	) -> list[BinanceKlinesOutputSchema]:
		"""Get klines data from the API."""
		klines: Response = await self._get(parameters=parameters_schema.model_dump(by_alias=True), **kwargs)
		return [
			BinanceKlinesOutputSchema.from_kline(
				kline=kline,
				ticker=parameters_schema.ticker,
				section=parameters_schema.section,
				interval=parameters_schema.interval,
			)
			for kline in klines.json()
		]


class BinanceSpotAPIClient(BinanceAPIClientBase):
	"""Binance Spot API client."""

	@route("/api/v3/ping")
	async def ping(self, *args, **kwargs) -> None:
		"""Ping the Binance Spot API."""
		await super()._ping(*args, **kwargs)

	@route("/api/v3/klines")
	async def klines(
		self, parameters_schema: BinanceKlinesParametersSchema, **kwargs
	) -> list[BinanceKlinesOutputSchema]:
		"""Get klines from Binance Spot API."""
		return await super()._klines(parameters_schema=parameters_schema, **kwargs)


class BinanceUsdtmAPIClient(BinanceAPIClientBase):
	"""Binance USDT-M Futures API client."""

	@route("/fapi/v1/ping")
	async def ping(self, *args, **kwargs) -> None:
		"""Ping the Binance USDT-M Futures API."""
		await super()._ping(*args, **kwargs)

	@route("/fapi/v1/klines")
	async def klines(
		self, parameters_schema: BinanceKlinesParametersSchema, **kwargs
	) -> list[BinanceKlinesOutputSchema]:
		"""Get klines from Binance USDT-M Futures API."""
		return await super()._klines(parameters_schema=parameters_schema, **kwargs)
