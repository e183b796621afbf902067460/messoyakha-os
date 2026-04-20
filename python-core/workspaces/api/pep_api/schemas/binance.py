from datetime import datetime, timedelta, timezone
from typing import Final, TypeAlias

from pydantic import BaseModel, Field, field_serializer

from pep_api.enums.binance import BinanceIntervalEnum, BinanceMarketEnum


_MILLISECONDS_IN_SECOND: Final[int] = 10**3


class _BinanceKlinesParametersSchemaBase(BaseModel):
	"""Parameters schema for Binance klines endpoint."""

	ticker: str = Field(serialization_alias="symbol")
	market: BinanceMarketEnum = Field(init=False, exclude=True)
	interval: BinanceIntervalEnum

	start_time: datetime = Field(serialization_alias="startTime")
	end_time: datetime = Field(serialization_alias="endTime")

	limit: int | None = Field(default=1_000)

	@field_serializer("start_time")
	def serialize_start_time_to_milliseconds(self, start_time: int | datetime) -> int | None:
		"""Serialize start_time to milliseconds since epoch."""
		if isinstance(start_time, datetime):
			return int(start_time.timestamp() * _MILLISECONDS_IN_SECOND)
		return start_time

	@field_serializer("end_time")
	def serialize_end_time_to_milliseconds(self, end_time: int | datetime) -> int | None:
		"""Serialize end_time to milliseconds since epoch."""
		if isinstance(end_time, datetime):
			return int(end_time.timestamp() * _MILLISECONDS_IN_SECOND)
		return end_time

	@property
	def delta(self) -> timedelta:
		"""Get time delta between end_time and start_time."""
		return self.end_time - self.start_time

	@property
	def interval_seconds(self) -> float:
		if self.interval == BinanceIntervalEnum.THIRTY_MINUTES:
			return timedelta(minutes=30).total_seconds()
		if self.interval == BinanceIntervalEnum.ONE_HOUR:
			return timedelta(hours=1).total_seconds()
		if self.interval == BinanceIntervalEnum.TWO_HOURS:
			return timedelta(hours=2).total_seconds()
		if self.interval == BinanceIntervalEnum.FOUR_HOURS:
			return timedelta(hours=4).total_seconds()
		if self.interval == BinanceIntervalEnum.ONE_DAY:
			return timedelta(days=1).total_seconds()
		if self.interval == BinanceIntervalEnum.ONE_WEEK:
			return timedelta(weeks=1).total_seconds()
		raise ValueError("Inappropriate interval set (pep-api).")


class BinanceKlinesSpotParametersSchema(_BinanceKlinesParametersSchemaBase):
	"""Parameters schema for Binance spot market klines endpoint."""

	market: BinanceMarketEnum = Field(default=BinanceMarketEnum.SPOT, init=False, exclude=True)


class BinanceKlinesUSDTMParametersSchema(_BinanceKlinesParametersSchemaBase):
	"""Parameters schema for Binance USDT-M futures market klines endpoint."""

	market: BinanceMarketEnum = Field(default=BinanceMarketEnum.USDTM, init=False, exclude=True)


class BinanceKlinesOutputSchema(BaseModel):
	"""Output schema for Binance klines data."""

	ticker: str
	market: BinanceMarketEnum
	interval: BinanceIntervalEnum

	open: float
	high: float
	low: float
	close: float
	volume: float

	open_time: datetime
	close_time: datetime

	@staticmethod
	def from_kline(
		kline: list, ticker: str, market: BinanceMarketEnum, interval: BinanceIntervalEnum
	) -> "BinanceKlinesOutputSchema":
		"""Create output schema from raw kline data."""
		return BinanceKlinesOutputSchema(
			ticker=ticker,
			market=market,
			interval=interval,
			open=kline[1],
			high=kline[2],
			low=kline[3],
			close=kline[4],
			volume=kline[5],
			open_time=datetime.fromtimestamp(kline[0] / _MILLISECONDS_IN_SECOND, tz=timezone.utc),
			close_time=datetime.fromtimestamp(kline[6] / _MILLISECONDS_IN_SECOND, tz=timezone.utc),
		)


BinanceKlinesParametersSchema: TypeAlias = BinanceKlinesSpotParametersSchema | BinanceKlinesUSDTMParametersSchema
