from datetime import datetime

from pandera.polars import DataFrameModel, Field


class OHLCVSchema(DataFrameModel):
    open: float
    high: float
    low: float
    close: float
    volume: float

    timestamp: datetime

    partition_by_ticker: str = Field(alias="_partition_by_ticker")
    partition_by_interval: str = Field(alias="_partition_by_interval")
    partition_by_product: str = Field(alias="_partition_by_product")
    partition_by_venue: str = Field(alias="_partition_by_venue")
    partition_by_currency: str = Field(alias="_partition_by_currency")
    partition_by_month: int = Field(alias="_partition_by_month")
    partition_by_year: int = Field(alias="_partition_by_year")

    class Config:  # type: ignore[bad-override]
        strict = "filter"
        coerce = True
