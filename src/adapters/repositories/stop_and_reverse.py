from _duckdb import HTTPException, InvalidInputException, IOException  # noqa: WPS436
from pandas import DataFrame

from src.adapters.repositories.common.duckdb_base import DuckDBBaseRepository
from src.schemas.queries import SARQueryParametersSchema, SARTrialsQueryParametersSchema


# pylint: disable=duplicate-code
class SARRepository(DuckDBBaseRepository):
    def query_stops_and_reverses(self, path: str, parameters_schema: SARQueryParametersSchema) -> DataFrame | None:
        query: str = f"""
            SELECT
                exchange,
                section,
                ticker,
                interval,

                sar,

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
        stops_and_reverses: DataFrame | None = None
        try:
            stops_and_reverses = self._query_dataframe(query=query, parameters=parameters_schema.to_list())
        except (HTTPException, IOException, InvalidInputException):
            ...  # noqa: WPS428
        return stops_and_reverses

    def query_stop_and_reverse_trials(
        self, path: str, parameters_schema: SARTrialsQueryParametersSchema
    ) -> DataFrame | None:
        query: str = f"""
            SELECT
                exchange,
                section,
                ticker,
                interval,

                value,

                startvalue,
                offsetonreverse,

                accelerationinitlong,
                accelerationinitshort,

                accelerationlong,
                accelerationshort,

                accelerationmaxlong,
                accelerationmaxshort,

                state
            FROM
                read_parquet({path!r})
            WHERE
                exchange = ? AND
                section = ? AND
                ticker = ? AND
                interval = ?
            ORDER BY
                value DESC;
        """  # noqa: S608
        stop_and_reverse_trials: DataFrame | None = None
        try:
            stop_and_reverse_trials = self._query_dataframe(query=query, parameters=parameters_schema.to_list())
        except (HTTPException, IOException, InvalidInputException):
            ...  # noqa: WPS428
        return stop_and_reverse_trials


# pylint: enable=duplicate-code
