from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_serializer, field_validator


class CBRKeyRateParametersSchema(BaseModel):
    start_time: datetime = Field(serialization_alias="fromDate")
    end_time: datetime = Field(serialization_alias="ToDate")

    @field_serializer("start_time")
    def _serialize_start_time_to_str(self, start_time: datetime) -> str:
        if isinstance(start_time, datetime):
            return start_time.strftime("%Y-%m-%d")
        return start_time

    @field_serializer("end_time")
    def _serialize_end_time_to_str(self, end_time: datetime) -> str:
        if isinstance(end_time, datetime):
            return end_time.strftime("%Y-%m-%d")
        return end_time


class CBRInterestRateInputSchema(BaseModel):
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
