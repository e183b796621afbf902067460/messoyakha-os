import warnings
from io import BytesIO

from attrs import define, field
from babel.dates import get_month_names
from nautilus_trader.model.currencies import RUB
from pandas import (
    DataFrame as PdDf,
    Series,
    isna,
    read_excel,
)
from polars import (
    DataFrame as PlDf,
    col,
    datetime as pl_datetime,
    from_pandas,
    lit,
)
from pydantic import BaseModel

from messoyakha_fedstat_sdk.adapters.fedstat import FedstatAPIClient
from messoyakha_fedstat_sdk.schemas.inflation_rate import (
    FedstatInflationRateDataSchema,
    FedstatInflationRateInputSchema,
    FedstatInflationRateParametersSchema,
)


warnings.filterwarnings("ignore")


class _InflationRateRowSchema(BaseModel):
    year: int
    month: int
    rate: float


def _parse_fedstat_excel_to_dataframe(fedstat_excel: PdDf) -> PdDf:  # noqa: C901
    russian_months: list[str] = list(get_month_names(width="wide", context="stand-alone", locale="ru").values())

    year_column_id: int | None = None
    month_column_id: int | None = None
    for row in fedstat_excel.itertuples():
        for value in row[1:]:
            value_as_string = str(value).strip().lower()
            if value_as_string.isdigit() and len(value_as_string) == 4:  # noqa: PLR2004
                year_column_id = row.Index  # pyrefly: ignore[bad-assignment, missing-attribute]
            if value_as_string in russian_months:
                month_column_id = row.Index  # pyrefly: ignore[bad-assignment, missing-attribute]
    if not year_column_id or not month_column_id:
        return PdDf(columns=["year", "month", "inflation_rate"])
    year_row: Series = fedstat_excel.iloc[year_column_id]
    month_row: Series = fedstat_excel.iloc[month_column_id]

    years: dict[int, int] = {}
    current_year: int | None = None
    for id, _ in enumerate(year_row):
        value = str(year_row[id])
        if value.isdigit() and len(value) == 4:  # noqa: PLR2004
            current_year = int(value)
        if current_year:
            years[id] = current_year

    months: dict[int, int] = {}
    for id, _ in enumerate(month_row):
        value = str(month_row[id]).strip().lower()
        if value in russian_months:
            months[id] = russian_months.index(value) + 1

    inflation_rates: list[_InflationRateRowSchema] = []
    for row in fedstat_excel.itertuples():
        if row.Index <= month_column_id:  # pyrefly: ignore[unsupported-operation, missing-attribute]
            continue
        region: str | None = row[1]
        if isna(region):
            continue
        for id, month in months.items():
            year: int | None = years.get(id)
            if year:
                value = row[id + 1]
                inflation_rates.append(_InflationRateRowSchema(year=year, month=month, rate=float(value)))
    return PdDf([inflation_rate.model_dump() for inflation_rate in inflation_rates])


@define(slots=True, auto_attribs=True, kw_only=True)
class FedstatService:
    _client: FedstatAPIClient = field(init=False, factory=FedstatAPIClient)

    async def get_inflation_rate(self, input_schema: FedstatInflationRateInputSchema) -> PlDf:
        fedstat_excel: PdDf = read_excel(
            BytesIO(
                await self._client.inflation_rate(
                    data_schema=FedstatInflationRateDataSchema(
                        start_date=input_schema.start_date, end_date=input_schema.end_date
                    ),
                    parameters_schema=FedstatInflationRateParametersSchema(),
                )
            ),
            engine="xlrd",
        )
        inflation_rate: PlDf = from_pandas(_parse_fedstat_excel_to_dataframe(fedstat_excel=fedstat_excel))
        return (
            inflation_rate.with_columns(
                lit(str(RUB)).alias("currency"),
                (col("rate") - 100) / 100,
                pl_datetime(col("year"), col("month"), 1, time_zone="UTC").alias("timestamp"),
            )
            .filter(col("timestamp").is_between(input_schema.start_date, input_schema.end_date))
            .drop("year", "month")
            .unique()
            .sort(by=col("timestamp"))
        )
