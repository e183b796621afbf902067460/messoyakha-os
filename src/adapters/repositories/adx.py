from _duckdb import HTTPException, InvalidInputException, IOException  # noqa: WPS436
from pandas import DataFrame

from src.adapters.repositories.common.duckdb_base import DuckDBBaseRepository
from src.schemas.queries import ADXQueryParametersSchema


# pylint: disable=duplicate-code
class ADXRepository(DuckDBBaseRepository):
    def query_adx(self, path: str, parameters_schema: ADXQueryParametersSchema) -> DataFrame | None:
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
                datetime   ASC;
        """  # noqa: S608
        adx: DataFrame | None = None
        try:
            adx = self._query_dataframe(query=query, parameters=parameters_schema.to_list())
        except (HTTPException, IOException, InvalidInputException):
            ...  # noqa: WPS428
        if isinstance(adx, DataFrame):
            adx.drop(columns=["exchange_1", "section_1", "ticker_1", "interval_1", "datetime_1"], axis=1, inplace=True)
        return adx


# pylint: enable=duplicate-code
