from _duckdb import HTTPException, InvalidInputException, IOException  # noqa: WPS436
from pandas import DataFrame

from src.adapters.repositories.common.duckdb_base import DuckDBBaseRepository
from src.schemas.filters import (
    ADXQueryParametersSchema,
    AroonQueryParametersSchema,
    BinaryQueryParametersSchema,
    MAQueryParametersSchema,
    MDIQueryParametersSchema,
    PDIQueryParametersSchema,
    QueryParametersBaseSchema,
    RSIQueryParametersSchema,
    StreakQueryParametersSchema,
)


# pylint: disable=duplicate-code
class IndicatorsBaseRepository(DuckDBBaseRepository):
    def _query_indicators(self, path: str, parameters_schema: QueryParametersBaseSchema) -> DataFrame | None:
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
        indicators: DataFrame | None = None
        try:
            indicators = self._query_dataframe(query=query, parameters=parameters_schema.to_list())
        except (HTTPException, IOException, InvalidInputException):
            ...  # noqa: WPS428
        if isinstance(indicators, DataFrame):
            indicators.drop(
                columns=["exchange_1", "section_1", "ticker_1", "interval_1", "datetime_1"], axis=1, inplace=True
            )
        return indicators


class MARepository(IndicatorsBaseRepository):
    def query_ma(self, path: str, parameters_schema: MAQueryParametersSchema) -> DataFrame | None:
        return self._query_indicators(path=path, parameters_schema=parameters_schema)


class ADXRepository(IndicatorsBaseRepository):
    def query_adx(self, path: str, parameters_schema: ADXQueryParametersSchema) -> DataFrame | None:
        return self._query_indicators(path=path, parameters_schema=parameters_schema)


class MDIRepository(IndicatorsBaseRepository):
    def query_mdi(self, path: str, parameters_schema: MDIQueryParametersSchema) -> DataFrame | None:
        return self._query_indicators(path=path, parameters_schema=parameters_schema)


class PDIRepository(IndicatorsBaseRepository):
    def query_pdi(self, path: str, parameters_schema: PDIQueryParametersSchema) -> DataFrame | None:
        return self._query_indicators(path=path, parameters_schema=parameters_schema)


class RSIRepository(IndicatorsBaseRepository):
    def query_rsi(self, path: str, parameters_schema: RSIQueryParametersSchema) -> DataFrame | None:
        return self._query_indicators(path=path, parameters_schema=parameters_schema)


class AroonRepository(IndicatorsBaseRepository):
    def query_aroon(self, path: str, parameters_schema: AroonQueryParametersSchema) -> DataFrame | None:
        return self._query_indicators(path=path, parameters_schema=parameters_schema)


class BinariesRepository(IndicatorsBaseRepository):
    def query_binaries(self, path: str, parameters_schema: BinaryQueryParametersSchema) -> DataFrame | None:
        return self._query_indicators(path=path, parameters_schema=parameters_schema)


class StreaksRepository(IndicatorsBaseRepository):
    def query_streaks(self, path: str, parameters_schema: StreakQueryParametersSchema) -> DataFrame | None:
        return self._query_indicators(path=path, parameters_schema=parameters_schema)


# pylint: enable=duplicate-code
