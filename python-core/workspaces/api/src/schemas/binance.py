from datetime import datetime, timedelta, timezone
from typing import Final

from pydantic import BaseModel, Field, field_serializer


_MILLISECONDS_IN_SECOND: Final[int] = 10**3


class BinanceKlinesParametersSchema(BaseModel):
	"""Parameters schema for Binance klines endpoint."""

	ticker: str = Field(serialization_alias="symbol")
	section: str = Field(exclude=True)
	interval: str

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


class BinanceKlinesOutputSchema(BaseModel):
	"""Output schema for Binance klines data."""

	ticker: str
	section: str
	interval: str

	open: float
	high: float
	low: float
	close: float
	volume: float

	open_time: datetime
	close_time: datetime

	@staticmethod
	def from_kline(kline: list, ticker: str, section: str, interval: str) -> "BinanceKlinesOutputSchema":
		"""Create output schema from raw kline data."""
		return BinanceKlinesOutputSchema(
			ticker=ticker,
			section=section,
			interval=interval,
			open=kline[1],
			high=kline[2],
			low=kline[3],
			close=kline[4],
			volume=kline[5],
			open_time=datetime.fromtimestamp(kline[0] / _MILLISECONDS_IN_SECOND, tz=timezone.utc),
			close_time=datetime.fromtimestamp(kline[6] / _MILLISECONDS_IN_SECOND, tz=timezone.utc),
		)
