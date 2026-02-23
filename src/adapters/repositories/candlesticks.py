from datetime import datetime

from polars import DataFrame, Datetime, col
from polars.exceptions import ComputeError

from src.adapters.repositories.common.polars_base import PolarsBaseRepository
from src.schemas.filters import LatestTimestampQueryParametersSchema, OHLCQueryParametersSchema


# pylint: disable=duplicate-code
class CandlesticksRepository(PolarsBaseRepository):
    def query_candlesticks(self, path: str, parameters_schema: OHLCQueryParametersSchema) -> DataFrame | None:
        try:
            candlesticks: DataFrame | None = (
                self.scan(paths=path)
                .filter(
                    col("exchange").eq(parameters_schema.exchange)
                    & col("section").eq(parameters_schema.section)
                    & col("ticker").eq(parameters_schema.ticker)
                    & col("interval").eq(parameters_schema.interval)
                )
                .with_columns(col("open_time").cast(Datetime))
                .select(col("*"))
                .collect(engine="streaming")
            )
        except ComputeError:
            return None
        return candlesticks

    def query_latest_timestamp(
        self, path: str, parameters_schema: LatestTimestampQueryParametersSchema
    ) -> datetime | None:
        try:
            latest_timestamp: DataFrame = (
                self.scan(paths=path)
                .filter(
                    col("exchange").eq(parameters_schema.exchange)
                    & col("section").eq(parameters_schema.section)
                    & col("ticker").eq(parameters_schema.ticker)
                    & col("interval").eq(parameters_schema.interval)
                )
                .select(col("close_time").max().alias("latest_timestamp"))
                .collect(engine="streaming")
            )
            if latest_timestamp.is_empty():
                return None
        except ComputeError:
            return None
        return latest_timestamp.item(0, "latest_timestamp")  # type: ignore[no-any-return]


# pylint: enable=duplicate-code
