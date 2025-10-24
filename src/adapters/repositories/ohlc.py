from datetime import datetime

from _duckdb import HTTPException, InvalidInputException, IOException  # noqa: WPS436
from pandas import DataFrame

from src.adapters.repositories.common.duckdb_base import DuckDBBaseRepository
from src.schemas.queries import LatestTimestampQueryParametersSchema, OHLCQueryParametersSchema


# pylint: disable=duplicate-code
class OHLCRepository(DuckDBBaseRepository):
    def query_candlesticks(self, path: str, parameters_schema: OHLCQueryParametersSchema) -> DataFrame | None:
        query: str = f"""
            SELECT
                exchange,
                section,
                ticker,
                interval,

                open,
                high,
                low,
                close,

                open_time,
                close_time
            FROM
                read_parquet({path!r})
            WHERE
                exchange = ? AND
                section = ? AND
                ticker = ? AND
                interval = ?
            ORDER BY
                open_time ASC;
        """  # noqa: S608
        candlesticks: DataFrame | None = None
        try:
            candlesticks = self._query_dataframe(query=query, parameters=parameters_schema.to_list())
        except (HTTPException, IOException, InvalidInputException):
            ...  # noqa: WPS428
        return candlesticks

    def query_latest_timestamp(
        self, path: str, parameters_schema: LatestTimestampQueryParametersSchema
    ) -> datetime | None:
        query: str = f"""
            SELECT
                CAST(STRFTIME(MAX(close_time), '%Y-%m-%d %H:%M:%S') AS DATETIME) AS latest_timestamp
            FROM
                read_parquet({path!r})
            WHERE
                exchange = ? AND
                section = ? AND
                ticker = ? AND
                interval = ?;
        """  # noqa: S608
        latest_timestamp: datetime | None = None
        try:
            latest_timestamp = self._query_dataframe(query=query, parameters=parameters_schema.to_list()).values[0][0]
        except (HTTPException, IOException, InvalidInputException):
            ...  # noqa: WPS428
        return latest_timestamp


# pylint: enable=duplicate-code
