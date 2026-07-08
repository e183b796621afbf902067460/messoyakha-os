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

from messoyakha_moex_iss_sdk.enums.intervals import MOEXIntervalEnum
from messoyakha_sdk.adapters.venues.misx import MISX
from messoyakha_sdk.enums.venues.misx import MISXProductEnum


class MOEXHistorySecurityHTTPEndpointSchema(BaseModel):
    ticker: str = Field(exclude=True)

    @computed_field(alias="security", repr=False)
    def _security(self) -> str:
        return self.ticker

    def _cohere_http_endpoint(self) -> None: ...


class MOEXHistorySecurityParametersSchema(BaseModel):
    currency: str = Field(exclude=True)
    product: MISXProductEnum = Field(exclude=True)

    interval: MOEXIntervalEnum

    start_time: datetime = Field(serialization_alias="from")
    end_time: datetime = Field(serialization_alias="till")

    class Config:
        use_enum_values = True

    @field_serializer("start_time")
    def _serialize_start_time(self, start_time: datetime) -> str:
        if isinstance(start_time, datetime):
            return start_time.strftime("%Y-%m-%d")
        return start_time

    @field_serializer("end_time")
    def _serialize_end_time(self, end_time: datetime) -> str:
        if isinstance(end_time, datetime):
            return end_time.strftime("%Y-%m-%d")
        return end_time


class MOEXHistorySecurityContextSchema(BaseModel):
    ticker: str
    currency: str
    product: MISXProductEnum
    interval: MOEXIntervalEnum


class MOEXHistorySecurityOutputSchema(BaseModel):
    venue: str = Field(init=False, default=MISX)
    interval: MOEXIntervalEnum

    ticker: str
    currency: str
    product: MISXProductEnum

    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None

    timestamp: datetime

    @model_validator(mode="wrap")
    @classmethod
    def _wrap(cls, row: list, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo) -> Self:
        data: dict = {
            "ticker": info.context["ticker"],  # type: ignore[unsupported-operation]
            "currency": info.context["currency"],  # type: ignore[unsupported-operation]
            "product": info.context["product"],  # type: ignore[unsupported-operation]
            "interval": info.context["interval"],  # type: ignore[unsupported-operation]
            "open": row[6],
            "high": row[7],
            "low": row[8],
            "close": row[5],
            "volume": row[17],
            "timestamp": row[2],
        }
        return handler(data)

    @field_validator("timestamp", mode="after")
    @classmethod
    def _update_timestamp_timezone(cls, timestamp: datetime) -> datetime:
        return timestamp.replace(tzinfo=timezone.utc)


class _MOEXHistorySecurityInputSchemaBase(BaseModel):
    interval: MOEXIntervalEnum = Field(init=False, default=MOEXIntervalEnum.ONE_DAY)

    ticker: str
    currency: str
    product: MISXProductEnum

    start_time: datetime
    end_time: datetime

    @property
    def delta(self) -> timedelta:
        return self.end_time - self.start_time

    @property
    def interval_seconds(self) -> float:
        if self.interval == MOEXIntervalEnum.ONE_DAY:
            return timedelta(days=1).total_seconds()
        raise ValueError("Inappropriate interval set.")

    @property
    def limit(self) -> timedelta:
        if self.interval == MOEXIntervalEnum.ONE_DAY:
            return timedelta(days=100)
        raise ValueError("Inappropriate interval set.")

    @field_validator("start_time", mode="after")
    @classmethod
    def _update_start_time_timezone(cls, start_time: datetime) -> datetime:
        return start_time.replace(tzinfo=timezone.utc)

    @field_validator("end_time", mode="after")
    @classmethod
    def _update_end_time_timezone(cls, end_time: datetime) -> datetime:
        return end_time.replace(tzinfo=timezone.utc)


class MOEXSpotHistorySecurityInputSchema(_MOEXHistorySecurityInputSchemaBase):
    product: MISXProductEnum = Field(init=False, default=MISXProductEnum.SPOT)


class MOEXFuturesHistorySecurityInputSchema(_MOEXHistorySecurityInputSchemaBase):
    product: MISXProductEnum = Field(init=False, default=MISXProductEnum.FUTURES)


MOEXHistorySecurityInputSchemaBase: TypeAlias = (
    MOEXSpotHistorySecurityInputSchema | MOEXFuturesHistorySecurityInputSchema
)
