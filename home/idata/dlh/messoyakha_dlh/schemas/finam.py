from datetime import datetime

from pandera.polars import DataFrameModel, Field


class FinamOHLCVSchema(DataFrameModel):
    open: float
    high: float
    low: float
    close: float
    volume: float

    timestamp: datetime

    partition_by_ticker: str = Field(alias="_partition_by_ticker")
    partition_by_market: str = Field(alias="_partition_by_market")
    partition_by_interval: str = Field(alias="_partition_by_interval")
    partition_by_year: int = Field(alias="_partition_by_year")
    partition_by_month: int = Field(alias="_partition_by_month")

    class Config:  # type: ignore[bad-override]
        strict = "filter"
        coerce = True
