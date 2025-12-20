from _duckdb import HTTPException, InvalidInputException, IOException  # noqa: WPS436
from pandas import DataFrame

from src.adapters.repositories.common.duckdb_base import DuckDBBaseRepository
from src.schemas.filters import SARTrialQueryParametersSchema


# pylint: disable=duplicate-code
class SARTrialsRepository(DuckDBBaseRepository):
    def query_sar_trials(self, path: str, parameters_schema: SARTrialQueryParametersSchema) -> DataFrame | None:
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
