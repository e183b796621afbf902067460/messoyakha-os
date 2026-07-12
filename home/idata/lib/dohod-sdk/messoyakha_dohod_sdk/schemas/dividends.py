from datetime import datetime, timezone
from typing import Self

from nautilus_trader.model.currencies import RUB
from pydantic import (
    BaseModel,
    Field,
    ModelWrapValidatorHandler,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_validator,
)

from messoyakha_sdk.adapters.venues.misx import MISX


class DohodDividendsEndpointSchema(BaseModel):
    ticker: str

    @field_serializer("ticker")
    def _serialize_ticker_to_lowercase(self, ticker: str) -> str:
        return ticker.lower()

    def _cohere_http_endpoint(self) -> None: ...


class DohodDividendsContextSchema(BaseModel):
    ticker: str
    venue: str
    currency: str


class DohodDividendsInputSchema(BaseModel):
    ticker: str
    venue: str = Field(init=False, default=MISX)
    currency: str = Field(init=False, default=str(RUB))


class DohodDividendsParametersSchema(BaseModel):
    venue: str
    currency: str


class DohodDividendsOutputSchema(BaseModel):
    ticker: str
    venue: str
    currency: str
    dividend: float
    timestamp: datetime

    @model_validator(mode="wrap")
    @classmethod
    def _wrap(
        cls, dividend: dict[str, str | None], handler: ModelWrapValidatorHandler[Self], info: ValidationInfo
    ) -> Self:
        data: dict = {
            "ticker": info.context["ticker"],  # type: ignore[unsupported-operation]
            "venue": info.context["venue"],  # type: ignore[unsupported-operation]
            "currency": info.context["currency"],  # type: ignore[unsupported-operation]
            "dividend": dividend["dividend"],
            "timestamp": dividend["timestamp"],
        }
        return handler(data)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp_with_timezone(cls, timestamp: str) -> datetime:
        return datetime.strptime(timestamp, "%d.%m.%Y").replace(tzinfo=timezone.utc)
