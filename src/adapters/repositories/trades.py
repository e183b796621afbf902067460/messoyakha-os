from _duckdb import HTTPException, InvalidInputException, IOException  # noqa: WPS436
from pandas import DataFrame

from src.adapters.repositories.common.duckdb_base import DuckDBBaseRepository
from src.schemas.filters import TradeQueryParametersSchema


# pylint: disable=duplicate-code
class TradesRepository(DuckDBBaseRepository):
    def query_trades(self, path: str, parameters_schema: TradeQueryParametersSchema) -> DataFrame | None:
        query: str = f"""
            SELECT
                exchange,
                section,
                ticker,
                interval,

                pct,
                is_long,
                ticks,

                datetime
            FROM
                read_parquet({path!r})
            WHERE
                exchange = ? AND
                section = ? AND
                ticker = ? AND
                interval = ?
            ORDER BY
                datetime ASC;
        """  # noqa: S608
        trades: DataFrame | None = None
        try:
            trades = self._query_dataframe(query=query, parameters=parameters_schema.to_list())
        except (HTTPException, IOException, InvalidInputException):
            ...  # noqa: WPS428
        return trades


# pylint: enable=duplicate-code
