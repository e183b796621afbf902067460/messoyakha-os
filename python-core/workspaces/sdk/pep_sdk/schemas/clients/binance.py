from datetime import datetime, timedelta, timezone
from typing import Final, Self, TypeAlias

from pydantic import (
    BaseModel,
    Field,
    ModelWrapValidatorHandler,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_validator,
)

from pep_sdk.enums.clients.binance import BinanceIntervalEnum, BinanceMarketEnum


_MILLISECONDS_IN_SECOND: Final[int] = 10**3


class BinanceKlinesParametersSchema(BaseModel):
    ticker: str = Field(serialization_alias="symbol")
    market: BinanceMarketEnum = Field(exclude=True)
    interval: BinanceIntervalEnum

    start_time: datetime = Field(serialization_alias="startTime")
    end_time: datetime = Field(serialization_alias="endTime")

    limit: int | None = Field(init=False, default=1_000)

    @field_serializer("start_time")
    def _serialize_start_time_to_milliseconds(self, start_time: int | datetime) -> int:
        if isinstance(start_time, datetime):
            return int(start_time.timestamp() * _MILLISECONDS_IN_SECOND)
        return start_time

    @field_serializer("end_time")
    def _serialize_end_time_to_milliseconds(self, end_time: int | datetime) -> int:
        if isinstance(end_time, datetime):
            return int(end_time.timestamp() * _MILLISECONDS_IN_SECOND)
        return end_time


class BinanceKlinesContextSchema(BaseModel):
    ticker: str
    market: BinanceMarketEnum
    interval: BinanceIntervalEnum


class _BinanceKlinesInputSchemaBase(BaseModel):
    ticker: str
    market: BinanceMarketEnum = Field(init=False)
    interval: BinanceIntervalEnum

    start_time: datetime
    end_time: datetime

    @property
    def delta(self) -> timedelta:
        return self.end_time - self.start_time

    @property
    def interval_seconds(self) -> float:
        if self.interval == BinanceIntervalEnum.ONE_HOUR:
            return timedelta(hours=1).total_seconds()
        if self.interval == BinanceIntervalEnum.FOUR_HOURS:
            return timedelta(hours=4).total_seconds()
        if self.interval == BinanceIntervalEnum.ONE_DAY:
            return timedelta(days=1).total_seconds()
        raise ValueError("Inappropriate interval set (pep-api).")

    @field_validator("start_time", mode="after")
    @classmethod
    def _update_start_time_timezone(cls, start_time: datetime) -> datetime:
        return start_time.replace(tzinfo=timezone.utc)

    @field_validator("end_time", mode="after")
    @classmethod
    def _update_end_time_timezone(cls, end_time: datetime) -> datetime:
        return end_time.replace(tzinfo=timezone.utc)


class BinanceKlinesSpotInputSchema(_BinanceKlinesInputSchemaBase):
    market: BinanceMarketEnum = Field(init=False, default=BinanceMarketEnum.SPOT)


class BinanceKlinesUSDTMInputSchema(_BinanceKlinesInputSchemaBase):
    market: BinanceMarketEnum = Field(init=False, default=BinanceMarketEnum.USDTM)


class BinanceKlinesOutputSchema(BaseModel):
    ticker: str
    market: BinanceMarketEnum
    interval: BinanceIntervalEnum

    open: float
    high: float
    low: float
    close: float
    volume: float

    timestamp: datetime

    @model_validator(mode="wrap")
    @classmethod
    def _wrap(cls, kline: list, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo) -> Self:
        data: dict = {
            "ticker": info.context["ticker"],  # type: ignore[unsupported-operation]
            "market": info.context["market"],  # type: ignore[unsupported-operation]
            "interval": info.context["interval"],  # type: ignore[unsupported-operation]
            "open": kline[1],
            "high": kline[2],
            "low": kline[3],
            "close": kline[4],
            "volume": kline[5],
            "timestamp": datetime.fromtimestamp(kline[0] / _MILLISECONDS_IN_SECOND, tz=timezone.utc),
        }
        return handler(data)

    @field_validator("timestamp", mode="after")
    @classmethod
    def _update_timestamp_timezone(cls, timestamp: datetime) -> datetime:
        return timestamp.replace(tzinfo=timezone.utc)


BinanceKlinesInputSchema: TypeAlias = BinanceKlinesSpotInputSchema | BinanceKlinesUSDTMInputSchema
