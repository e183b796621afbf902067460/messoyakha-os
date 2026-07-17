from datetime import datetime

from pandera.polars import DataFrameModel, Field


class FedstatInflationRateSchema(DataFrameModel):
    rate: float
    currency: str

    timestamp: datetime

    partition_by_month: int = Field(alias="_partition_by_month")
    partition_by_year: int = Field(alias="_partition_by_year")

    class Config:  # type: ignore[bad-override]
        strict = "filter"
        coerce = True
