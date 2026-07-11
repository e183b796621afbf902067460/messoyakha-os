from datetime import datetime, timedelta, timezone
from typing import Self, TypeAlias

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

from messoyakha_finam_sdk.enums.intervals import FinamIntervalEnum
from messoyakha_finam_sdk.schemas._common.headers import FinamAuthorizationHeaderSchemaBase
from messoyakha_sdk.adapters.venues.misx import MISX
from messoyakha_sdk.enums.venues.misx import MISXProductEnum


class FinamBarsHTTPEndpointSchema(BaseModel):
    ticker: str = Field(exclude=True)
    venue: str = Field(exclude=True)

    @computed_field(alias="symbol", repr=False)
    @property
    def _symbol(self) -> str:
        return f"{self.ticker}@{self.venue}"

    def _cohere_http_endpoint(self) -> None: ...


class FinamBarsHeadersSchema(FinamAuthorizationHeaderSchemaBase): ...


class FinamBarsParametersSchema(BaseModel):
    interval: FinamIntervalEnum = Field(serialization_alias="timeframe")
    product: MISXProductEnum = Field(exclude=True)
    venue: str = Field(exclude=True)
    currency: str = Field(exclude=True)

    start_time: datetime = Field(serialization_alias="interval.start_time")
    end_time: datetime = Field(serialization_alias="interval.end_time")

    @field_serializer("start_time")
    def _add_utc_timezone_to_start_time(self, start_time: datetime) -> str:
        if isinstance(start_time, datetime):
            return start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return start_time

    @field_serializer("end_time")
    def _add_utc_timezone_to_end_time(self, end_time: datetime) -> str:
        if isinstance(end_time, datetime):
            return end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return end_time


class FinamBarsContextSchema(BaseModel):
    ticker: str
    interval: FinamIntervalEnum
    product: MISXProductEnum
    venue: str
    currency: str


class FinamBarsOutputSchema(BaseModel):
    ticker: str
    interval: FinamIntervalEnum
    product: MISXProductEnum
    venue: str
    currency: str

    open: float
    high: float
    low: float
    close: float
    volume: float

    timestamp: datetime

    @model_validator(mode="wrap")
    @classmethod
    def _wrap(cls, bar: dict, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo) -> Self:
        data: dict = {
            "ticker": info.context["ticker"],  # type: ignore[unsupported-operation]
            "interval": info.context["interval"],  # type: ignore[unsupported-operation]
            "product": info.context["product"],  # type: ignore[unsupported-operation]
            "venue": info.context["venue"],  # type: ignore[unsupported-operation]
            "currency": info.context["currency"],  # type: ignore[unsupported-operation]
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
    def _update_timestamp_timezone(cls, timestamp: datetime) -> datetime:
        return timestamp.replace(tzinfo=timezone.utc)


class _FinamBarsInputSchema(BaseModel):
    secret: str

    ticker: str
    interval: FinamIntervalEnum
    product: MISXProductEnum
    venue: str
    currency: str

    start_time: datetime
    end_time: datetime

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

    @property
    def limit(self) -> timedelta:
        if self.interval == FinamIntervalEnum.ONE_HOUR:
            return timedelta(days=30)
        if self.interval == FinamIntervalEnum.FOUR_HOURS:
            return timedelta(days=30)
        if self.interval == FinamIntervalEnum.ONE_DAY:
            return timedelta(days=365)
        raise ValueError("Inappropriate interval set (pep-api).")

    @field_validator("start_time", mode="after")
    @classmethod
    def _update_start_time_timezone(cls, start_time: datetime) -> datetime:
        return start_time.replace(tzinfo=timezone.utc)

    @field_validator("end_time", mode="after")
    @classmethod
    def _update_end_time_timezone(cls, end_time: datetime) -> datetime:
        return end_time.replace(tzinfo=timezone.utc)


class FinamBarsMISXSpotInputSchema(_FinamBarsInputSchema):
    venue: str = Field(init=False, default=MISX)
    product: MISXProductEnum = Field(init=False, default=MISXProductEnum.SPOT)


class FinamBarsMISXFuturesInputSchema(_FinamBarsInputSchema):
    venue: str = Field(init=False, default=MISX)
    product: MISXProductEnum = Field(init=False, default=MISXProductEnum.FUTURES)


FinamBarsInputSchema: TypeAlias = FinamBarsMISXSpotInputSchema | FinamBarsMISXFuturesInputSchema
