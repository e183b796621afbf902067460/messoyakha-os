from datetime import datetime

from pandera.polars import DataFrameModel, Field


class DohodDividendsSchema(DataFrameModel):
    dividend: float

    timestamp: datetime

    partition_by_ticker: str = Field(alias="_partition_by_ticker")
    partition_by_venue: str = Field(alias="_partition_by_venue")
    partition_by_currency: str = Field(alias="_partition_by_currency")
    partition_by_month: int = Field(alias="_partition_by_month")
    partition_by_year: int = Field(alias="_partition_by_year")

    class Config:
        strict = "filter"
        coerce = True
