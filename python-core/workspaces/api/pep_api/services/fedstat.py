from io import BytesIO

from attrs import define, field
from pandas import DataFrame, read_excel

from pep_api.adapters.fedstat import FedstatAPIClient
from pep_api.schemas.fedstat import (
    FedstatInflationRateDataSchema,
    FedstatInflationRateInputSchema,
    FedstatInflationRateParametersSchema,
)


@define(slots=True, auto_attribs=True, kw_only=True)
class FedstatService:
    _client: FedstatAPIClient = field(init=False, factory=FedstatAPIClient)

    async def get_inflation_rate(self, input_schema: FedstatInflationRateInputSchema) -> DataFrame:
        inflation_rate: DataFrame = read_excel(
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
        return inflation_rate
