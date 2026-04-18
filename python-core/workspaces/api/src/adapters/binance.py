from httpx import Response

from pep_api.adapters.common.abc import APIClientBase, route
from pep_api.schemas.binance import BinanceKlinesInputSchema, BinanceKlinesOutputSchema


class BinanceAPIClientBase(APIClientBase):
	"""Binance API client base."""

	async def _ping(self, *args, **kwargs) -> None:  # type: ignore[method-assign]
		"""Ping the API endpoint."""
		await self._get(*args, **kwargs)

	async def _klines(self, *args, **kwargs) -> list[BinanceKlinesOutputSchema]:  # type: ignore[method-assign]  # noqa: ARG002
		"""Get klines data from the API."""
		input_schema: BinanceKlinesInputSchema = kwargs.pop("input_schema")
		endpoint: str = kwargs.pop("endpoint")
		parameters: dict = input_schema.model_dump(by_alias=True)
		klines: Response = await self._get(endpoint=endpoint, parameters=parameters, **kwargs)
		return [
			BinanceKlinesOutputSchema.from_kline(
				kline=kline, ticker=input_schema.ticker, section=input_schema.section, interval=input_schema.interval
			)
			for kline in klines.json()
		]


class BinanceSpotAPIClient(BinanceAPIClientBase):
	"""Binance Spot API client."""

	@route("/api/v3/ping")
	async def ping(self, *args, **kwargs) -> None:  # type: ignore[method-assign]
		"""Ping the Binance Spot API."""
		await super()._ping(*args, **kwargs)

	@route("/api/v3/klines")
	async def klines(self, *args, **kwargs) -> list[BinanceKlinesOutputSchema]:  # type: ignore[method-assign]
		"""Get klines from Binance Spot API."""
		return await super()._klines(*args, **kwargs)


class BinanceUsdtmAPIClient(BinanceAPIClientBase):
	"""Binance USDT-M Futures API client."""

	@route("/fapi/v1/ping")
	async def ping(self, *args, **kwargs) -> None:  # type: ignore[method-assign]
		"""Ping the Binance USDT-M Futures API."""
		await super()._ping(*args, **kwargs)

	@route("/fapi/v1/klines")
	async def klines(self, *args, **kwargs) -> list[BinanceKlinesOutputSchema]:  # type: ignore[method-assign]
		"""Get klines from Binance USDT-M Futures API."""
		return await super()._klines(*args, **kwargs)
