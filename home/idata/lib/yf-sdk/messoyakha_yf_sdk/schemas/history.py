from datetime import datetime, timezone

from pydantic import BaseModel, field_validator

from messoyakha_yf_sdk.enums.intervals import YFIntervalEnum


class YFHistoryOutputSchema(BaseModel):
    ticker: str
    interval: YFIntervalEnum
    venue: str
    product: str
    currency: str

    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None

    timestamp: datetime

    @field_validator("timestamp", mode="after")
    @classmethod
    def _update_timestamp_timezone(cls, timestamp: datetime) -> datetime:
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)


class YFHistoryInputSchema(BaseModel):
    ticker: str
    interval: YFIntervalEnum
    venue: str
    product: str
    currency: str

    start_time: datetime
    end_time: datetime

    @field_validator("start_time", mode="after")
    @classmethod
    def _update_start_time_timezone(cls, start_time: datetime) -> datetime:
        if start_time.tzinfo is None:
            return start_time.replace(tzinfo=timezone.utc)
        return start_time.astimezone(timezone.utc)

    @field_validator("end_time", mode="after")
    @classmethod
    def _update_end_time_timezone(cls, end_time: datetime) -> datetime:
        if end_time.tzinfo is None:
            return end_time.replace(tzinfo=timezone.utc)
        return end_time.astimezone(timezone.utc)
