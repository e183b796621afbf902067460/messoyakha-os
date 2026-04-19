from asyncio import sleep
from datetime import datetime, timedelta

from attr import attrs
from numpy import floor
from polars import DataFrame

from pep_api.adapters.binance import BinanceAPIClient
from pep_api.schemas.binance import BinanceKlinesOutputSchema, BinanceKlinesParametersSchema


def _convert_binance_interval_to_seconds(interval: str) -> float:
	if interval == "30m":
		return timedelta(minutes=30).total_seconds()
	if interval == "1h":
		return timedelta(hours=1).total_seconds()
	if interval == "2h":
		return timedelta(hours=2).total_seconds()
	if interval == "4h":
		return timedelta(hours=4).total_seconds()
	if interval == "1d":
		return timedelta(days=1).total_seconds()
	if interval == "1w":
		return timedelta(weeks=1).total_seconds()
	raise ValueError(f"Invalid interval `{interval}` were passed (pep-api).")


@attrs(slots=True, auto_attribs=True, kw_only=True)
class BinanceService:
	"""Service for fetching OHLCV data from Binance."""

	_client: BinanceAPIClient

	async def get_ohlcv(self, parameters_schema: BinanceKlinesParametersSchema) -> DataFrame:
		"""Fetch OHLCV data for given input schema."""
		klines: list[BinanceKlinesOutputSchema] = []

		number_of_batches: int = int(
			floor(
				parameters_schema.delta.total_seconds()
				/ _convert_binance_interval_to_seconds(interval=parameters_schema.interval)
			)
		)
		for _ in range(number_of_batches):
			batch: list[BinanceKlinesOutputSchema] = await self._client.klines(parameters_schema=parameters_schema)
			if not batch:
				break

			next_start_time: datetime = batch[-1].close_time + timedelta(milliseconds=1)
			parameters_schema = BinanceKlinesParametersSchema(
				ticker=parameters_schema.ticker,
				section=parameters_schema.section,
				interval=parameters_schema.interval,
				start_time=next_start_time,
				end_time=parameters_schema.end_time,
			)

			klines.extend(batch)
			await sleep(0.25)
		return DataFrame([kline.model_dump() for kline in klines])
