from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, ModelWrapValidatorHandler, ValidationInfo, field_serializer, model_validator

from pep_api.enums.finam import FinamTimeframeEnum


_BEARER: Literal["Bearer"] = "Bearer"


class FinamSessionsJsonSchema(BaseModel):
    secret: str


class FinamSessionsOutputSchema(BaseModel):
    token: str


class FinamBarsEndpointSchema(BaseModel):
    ticker: str


class FinamBarsHeadersSchema(BaseModel):
    authorization: str = Field(serialization_alias="Authorization")

    @field_serializer("authorization")
    def add_bearer_to_authorization_at_serialization(self, authorization: str) -> str:
        if _BEARER not in authorization:
            return f"{_BEARER} {authorization}"
        return authorization


class FinamBarsParametersSchema(BaseModel):
    timeframe: FinamTimeframeEnum

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


class FinamBarsOutputSchema(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: float

    timestamp: datetime

    @model_validator(mode="wrap")
    @classmethod
    def __wrap_bar(cls, bar: dict, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo) -> Self:  # noqa: ARG003 unused arguement
        data: dict = {
            "timestamp": bar.get("timestamp"),
            "open": bar["open"]["value"],
            "high": bar["high"]["value"],
            "low": bar["low"]["value"],
            "close": bar["close"]["value"],
            "volume": bar["volume"]["value"],
        }
        return handler(data)


class FinamBarsInputSchema(BaseModel):
    secret: str

    ticker: str
    timeframe: FinamTimeframeEnum

    start_time: datetime
    end_time: datetime
