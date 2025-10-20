from _duckdb import HTTPException, IOException  # noqa: WPS436
from pandas import DataFrame

from src.adapters.repositories.common.duckdb_base import DuckDBBaseRepository
from src.schemas.queries import MovingAveragesQueryParametersSchema


# pylint: disable=duplicate-code
class MovingAveragesRepository(DuckDBBaseRepository):
    def query_moving_averages(
        self, path: str, parameters_schema: MovingAveragesQueryParametersSchema
    ) -> DataFrame | None:
        query: str = f"""
            SELECT
                exchange,
                section,
                ticker,
                interval,

                *,

                datetime
            FROM
                read_parquet({path!r})
            WHERE
                exchange = ? AND
                section = ? AND
                ticker = ? AND
                interval = ?
            ORDER BY
                date ASC
        """  # noqa: S608
        moving_averages: DataFrame | None = None
        try:
            moving_averages = self._query_dataframe(query=query, parameters=parameters_schema.to_list())
        except (HTTPException, IOException):
            ...  # noqa: WPS428
        return moving_averages


# pylint: enable=duplicate-code
