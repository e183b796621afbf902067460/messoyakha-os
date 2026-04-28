from datetime import datetime, timedelta, timezone
from typing import Self

from pydantic import (
    BaseModel,
    Field,
    ModelWrapValidatorHandler,
    ValidationInfo,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from pep_api.enums.finam import FinamIntervalEnum, FinamMarketEnum
from pep_api.schemas.common.endpoints import EndpointSchemaBase
from pep_api.schemas.common.headers import AuthorizationHeaderSchemaBase


class FinamSessionsJsonSchema(BaseModel):
    secret: str


class FinamSessionsOutputSchema(BaseModel):
    token: str


class FinamBarsEndpointSchema(EndpointSchemaBase):
    ticker: str = Field(exclude=True)
    market: FinamMarketEnum = Field(exclude=True)

    @computed_field(alias="symbol", repr=False)
    @property
    def symbol(self) -> str:
        return f"{self.ticker}@{self.market}"


class FinamClockHeadersSchema(AuthorizationHeaderSchemaBase): ...


class FinamBarsHeadersSchema(AuthorizationHeaderSchemaBase): ...


class FinamBarsParametersSchema(BaseModel):
    interval: FinamIntervalEnum = Field(serialization_alias="timeframe")

    start_time: datetime = Field(serialization_alias="interval.start_time")
    end_time: datetime = Field(serialization_alias="interval.end_time")

    @field_serializer("start_time")
    def add_utc_timezone_to_start_time(self, start_time: datetime) -> str:
        if isinstance(start_time, datetime):
            return start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return start_time

    @field_serializer("end_time")
    def add_utc_timezone_to_end_time(self, end_time: datetime) -> str:
        if isinstance(end_time, datetime):
            return end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return end_time


class FinamBarsContextSchema(BaseModel):
    ticker: str
    market: FinamMarketEnum
    interval: FinamIntervalEnum


class FinamBarsOutputSchema(BaseModel):
    ticker: str
    market: FinamMarketEnum
    interval: FinamIntervalEnum

    open: float
    high: float
    low: float
    close: float
    volume: float

    timestamp: datetime

    @model_validator(mode="wrap")
    @classmethod
    def __wrap_bar(cls, bar: dict, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo) -> Self:
        data: dict = {
            "ticker": info.context["ticker"],  # type: ignore[unsupported-operation]
            "market": info.context["market"],  # type: ignore[unsupported-operation]
            "interval": info.context["interval"],  # type: ignore[unsupported-operation]
            "open": bar["open"]["value"],
            "high": bar["high"]["value"],
            "low": bar["low"]["value"],
            "close": bar["close"]["value"],
            "volume": bar["volume"]["value"],
            "timestamp": bar["timestamp"],
        }
        return handler(data)

    @field_validator("timestamp", mode="after")
    @classmethod
    def update_timestamp_timezone(cls, timestamp: datetime) -> datetime:
        return timestamp.replace(tzinfo=timezone.utc)


class _FinamSecretInputSchemaBase(BaseModel):
    secret: str


class FinamPingInputSchema(_FinamSecretInputSchemaBase): ...


class FinamBarsInputSchema(_FinamSecretInputSchemaBase):
    ticker: str
    market: FinamMarketEnum
    interval: FinamIntervalEnum

    start_time: datetime
    end_time: datetime

    limit: timedelta = Field(init=False, default=timedelta(days=30))

    @property
    def delta(self) -> timedelta:
        return self.end_time - self.start_time

    @property
    def interval_seconds(self) -> float:
        if self.interval == FinamIntervalEnum.ONE_HOUR:
            return timedelta(hours=1).total_seconds()
        if self.interval == FinamIntervalEnum.FOUR_HOURS:
            return timedelta(hours=4).total_seconds()
        if self.interval == FinamIntervalEnum.ONE_DAY:
            return timedelta(days=1).total_seconds()
        raise ValueError("Inappropriate interval set (pep-api).")

    @field_validator("start_time", mode="after")
    @classmethod
    def update_start_time_timezone(cls, start_time: datetime) -> datetime:
        return start_time.replace(tzinfo=timezone.utc)

    @field_validator("end_time", mode="after")
    @classmethod
    def update_end_time_timezone(cls, end_time: datetime) -> datetime:
        return end_time.replace(tzinfo=timezone.utc)
