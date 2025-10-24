from _duckdb import HTTPException, InvalidInputException, IOException  # noqa: WPS436
from pandas import DataFrame

from src.adapters.repositories.common.duckdb_base import DuckDBBaseRepository
from src.schemas.queries import MAQueryParametersSchema


# pylint: disable=duplicate-code
class MARepository(DuckDBBaseRepository):
    def query_moving_averages(self, path: str, parameters_schema: MAQueryParametersSchema) -> DataFrame | None:
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
                datetime ASC;
        """  # noqa: S608
        moving_averages: DataFrame | None = None
        try:
            moving_averages = self._query_dataframe(query=query, parameters=parameters_schema.to_list())
        except (HTTPException, IOException, InvalidInputException):
            ...  # noqa: WPS428
        if isinstance(moving_averages, DataFrame):
            moving_averages.drop(
                columns=["exchange_1", "section_1", "ticker_1", "interval_1", "datetime_1"], axis=1, inplace=True
            )
        return moving_averages


# pylint: enable=duplicate-code
