from datetime import datetime

from pydantic import BaseModel, Field, field_serializer


class CBRKeyRateParametersSchema(BaseModel):
    start_time: datetime = Field(serialization_alias="fromDate")
    end_time: datetime = Field(serialization_alias="ToDate")

    @field_serializer("start_time")
    def serialize_start_time_to_str(self, start_time: datetime) -> str:
        if isinstance(start_time, datetime):
            return start_time.strftime("%Y-%m-%d")
        return start_time

    @field_serializer("end_time")
    def serialize_end_time_to_str(self, end_time: datetime) -> str:
        if isinstance(end_time, datetime):
            return end_time.strftime("%Y-%m-%d")
        return end_time


class CBRKeyRateOutputSchema(...): ...  # type: ignore[invalid-inheritance]
