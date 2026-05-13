from datetime import datetime, timezone
from typing import Final, Self

from pydantic import BaseModel, ModelWrapValidatorHandler, ValidationInfo, field_validator, model_validator


_ONE_BILLION: Final[int] = 10**9


class SmartLabNetIncomeEndpointSchema(BaseModel):
    ticker: str

    def _cohere_http_endpoint(self) -> None: ...


class SmartLabNetIncomeContextSchema(BaseModel):
    ticker: str


class SmartLabNetIncomeInputSchema(BaseModel):
    ticker: str


class SmartLabNetIncomeOutputSchema(BaseModel):
    ticker: str
    net_income: float | None
    timestamp: datetime

    @model_validator(mode="wrap")
    @classmethod
    def _wrap(
        cls, net_income: dict[str, str | None], handler: ModelWrapValidatorHandler[Self], info: ValidationInfo
    ) -> Self:
        data: dict = {
            "ticker": info.context["ticker"],
            "net_income": net_income["net_income"],
            "timestamp": net_income["timestamp"],
        }
        return handler(data)

    @field_validator("net_income", mode="after")
    @classmethod
    def _adjust_net_income_to_billions(cls, net_income: float | None) -> float | None:
        return net_income * _ONE_BILLION if net_income else net_income

    @field_validator("timestamp", mode="after")
    @classmethod
    def _update_timestamp_timezone(cls, timestamp: datetime) -> datetime:
        return timestamp.replace(tzinfo=timezone.utc)
