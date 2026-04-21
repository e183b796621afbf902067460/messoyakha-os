from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, model_validator

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


class _FinamBarsBarSchema(BaseModel):
	open: float
	high: float
	low: float
	close: float
	volume: float

	timestamp: datetime

	@model_validator(mode="before")
	def __unwrap(self, values: dict) -> dict:
		if isinstance(values, dict):
			return {
				"timestamp": values.get("timestamp"),
				"open": float(values["open"]["value"]),
				"high": float(values["high"]["value"]),
				"low": float(values["low"]["value"]),
				"close": float(values["close"]["value"]),
				"volume": float(values["volume"]["value"]),
			}
		return values


class FinamBarsOutputSchema(BaseModel):
	symbol: str
	bars: list[_FinamBarsBarSchema]
