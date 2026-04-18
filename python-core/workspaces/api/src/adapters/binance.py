from httpx import Response

from pep_api.adapters.common.abc import APIClientBase
from pep_api.schemas.binance import BinanceKlinesInputSchema, BinanceKlinesOutputSchema


class BinanceAPIClientBase(APIClientBase):
	_ping_endpoint: str
	_klines_endpoint: str

	async def ping(self) -> None:
		await self._get(endpoint=self._ping_endpoint)

	async def klines(self, input_schema: BinanceKlinesInputSchema) -> list[BinanceKlinesOutputSchema]:
		klines: Response | None = await self._get(
			endpoint=self._klines_endpoint, parameters=input_schema.model_dump(by_alias=True)
		)
		return [
			BinanceKlinesOutputSchema.from_kline(
				kline=kline, ticker=input_schema.ticker, section=input_schema.section, interval=input_schema.interval
			)
			for kline in klines.json()  # type: ignore[union-attr]
		]


class BinanceSpotAPIClient(BinanceAPIClientBase):
	_ping_endpoint: str = "/api/v3/ping"

	# https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints#klinecandlestick-data
	_klines_endpoint: str = "/api/v3/klines"


class BinanceUsdtmAPIClient(BinanceAPIClientBase):
	_ping_endpoint: str = "/fapi/v1/ping"

	# https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data
	_klines_endpoint: str = "/fapi/v1/klines"
