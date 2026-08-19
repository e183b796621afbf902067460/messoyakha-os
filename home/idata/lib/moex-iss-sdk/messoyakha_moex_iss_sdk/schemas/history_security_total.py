from datetime import datetime, timezone
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

from messoyakha_sdk.adapters.venues.misx import MISX


class MOEXHistorySecurityTotalHTTPEndpointSchema(BaseModel):
    ticker: str = Field(exclude=True)

    @computed_field(alias="security", repr=False)
    def _security(self) -> str:
        return self.ticker

    def _cohere_http_endpoint(self) -> None: ...


class MOEXHistorySecurityTotalParametersSchema(BaseModel):
    currency: str = Field(exclude=True)

    start_time: datetime = Field(serialization_alias="from")
    end_time: datetime = Field(serialization_alias="till")

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


class MOEXHistorySecurityTotalContextSchema(BaseModel):
    ticker: str
    currency: str


class MOEXHistorySecurityTotalOutputSchema(BaseModel):
    ticker: str
    venue: str = Field(init=False, default=MISX)
    currency: str
    total_supply: float | None
    timestamp: datetime

    @model_validator(mode="wrap")
    @classmethod
    def _wrap(cls, row: list, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo) -> Self:
        data: dict = {
            "ticker": info.context["ticker"],  # type: ignore[unsupported-operation]
            "currency": info.context["currency"],  # type: ignore[unsupported-operation]
            "total_supply": row[19],
            "timestamp": row[1],
        }
        return handler(data)

    @field_validator("timestamp", mode="after")
    @classmethod
    def _update_timestamp_timezone(cls, timestamp: datetime) -> datetime:
        return timestamp.replace(tzinfo=timezone.utc)


class MOEXHistorySecurityTotalInputSchema(BaseModel):
    ticker: str
    currency: str
    start_time: datetime
    end_time: datetime

    @field_validator("start_time", mode="after")
    @classmethod
    def _update_start_time_timezone(cls, start_time: datetime) -> datetime:
        return start_time.replace(tzinfo=timezone.utc)

    @field_validator("end_time", mode="after")
    @classmethod
    def _update_end_time_timezone(cls, end_time: datetime) -> datetime:
        return end_time.replace(tzinfo=timezone.utc)
