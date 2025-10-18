from datetime import datetime, timedelta

from pydantic import BaseModel, Field, field_serializer

from src.settings import settings


class BinanceKlinesInputSchema(BaseModel):

    ticker: str = Field(serialization_alias="symbol")
    section: str = Field(exclude=True)
    interval: str

    start_time: datetime = Field(serialization_alias="startTime")
    end_time: datetime = Field(serialization_alias="endTime")

    limit: int | None = Field(default=1_000)

    @field_serializer("start_time")  # type: ignore
    def serialize_start_time_to_milliseconds(self, start_time: int | datetime) -> int | None:
        if isinstance(start_time, datetime):
            return int(start_time.timestamp() * settings.MILLISECONDS_IN_SECOND)
        return start_time

    @field_serializer("end_time")  # type: ignore
    def serialize_end_time_to_milliseconds(self, end_time: int | datetime) -> int | None:
        if isinstance(end_time, datetime):
            return int(end_time.timestamp() * settings.MILLISECONDS_IN_SECOND)
        return end_time

    @property
    def delta(self) -> timedelta:
        return self.end_time - self.start_time


class BinanceKlinesOutputSchema(BaseModel):

    ticker: str
    section: str
    interval: str

    open: float
    high: float
    low: float
    close: float

    open_time: datetime
    close_time: datetime

    @staticmethod
    def from_kline(kline: list, ticker: str, section: str, interval: str) -> "BinanceKlinesOutputSchema":
        return BinanceKlinesOutputSchema(
            ticker=ticker,
            section=section,
            interval=interval,
            open=kline[1],
            high=kline[2],
            low=kline[3],
            close=kline[4],
            open_time=datetime.fromtimestamp(kline[0] / settings.MILLISECONDS_IN_SECOND),
            close_time=datetime.fromtimestamp(kline[6] / settings.MILLISECONDS_IN_SECOND),
        )
