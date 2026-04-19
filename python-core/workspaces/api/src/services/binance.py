from asyncio import sleep
from datetime import datetime, timedelta

from attr import attr, attrs
from numpy import floor
from polars import DataFrame

from pep_api.adapters.binance import BinanceAPIClient, BinanceSpotAPIClient, BinanceUSDTMAPIClient
from pep_api.schemas.binance import BinanceKlinesOutputSchema, BinanceKlinesParametersSchema, BinanceMarketEnum


@attrs(slots=True, auto_attribs=True, kw_only=True)
class _BinanceServiceBase:
	"""Service for fetching OHLCV data from Binance."""

	_client: BinanceAPIClient = attr(init=False)
	_market: BinanceMarketEnum = attr(init=False)

	async def get_ohlcv(self, parameters_schema: BinanceKlinesParametersSchema) -> DataFrame:
		"""Fetch OHLCV data for given input schema."""
		parameters_schema.market = self._market

		number_of_batches: int = int(
			floor(parameters_schema.delta.total_seconds() / parameters_schema.interval_seconds)
		)

		klines: list[BinanceKlinesOutputSchema] = []
		for _ in range(number_of_batches):
			batch: list[BinanceKlinesOutputSchema] = await self._client.klines(parameters_schema=parameters_schema)
			if not batch:
				break
			next_start_time: datetime = batch[-1].close_time + timedelta(milliseconds=1)
			parameters_schema = BinanceKlinesParametersSchema(
				ticker=parameters_schema.ticker,
				market=parameters_schema.market,
				interval=parameters_schema.interval,
				start_time=next_start_time,
				end_time=parameters_schema.end_time,
			)
			klines.extend(batch)
			if parameters_schema.start_time > parameters_schema.end_time:
				break
			await sleep(0.25)
		return DataFrame([kline.model_dump() for kline in klines])


class BinanceSpotService(_BinanceServiceBase):
	"""Service to handle requests to Binance Spot."""

	_client: BinanceAPIClient = BinanceSpotAPIClient()
	_market: BinanceMarketEnum = BinanceMarketEnum.SPOT


class BinanceUSDTMService(_BinanceServiceBase):
	"""Service to handle requests to Binance USDT-M."""

	_client: BinanceAPIClient = BinanceUSDTMAPIClient()
	_market: BinanceMarketEnum = BinanceMarketEnum.USDTM
