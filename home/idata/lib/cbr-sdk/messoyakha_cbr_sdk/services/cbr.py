from io import BytesIO

from attrs import define, field
from nautilus_trader.model.currencies import RUB
from pandas import read_xml
from polars import DataFrame, col, from_pandas, lit

from messoyakha_cbr_sdk.adapters.cbr import CBRSOAPAPIClient
from messoyakha_cbr_sdk.schemas.key_rate import CBRInterestRateInputSchema, CBRKeyRateParametersSchema
from messoyakha_sdk.adapters.banks.cbr import CBR


@define(slots=True, auto_attribs=True, kw_only=True)
class CBRService:
    _client: CBRSOAPAPIClient = field(init=False, factory=CBRSOAPAPIClient)

    def get_interest_rates(self, input_schema: CBRInterestRateInputSchema) -> DataFrame:
        interest_rates: DataFrame = from_pandas(
            read_xml(
                BytesIO(
                    self._client.key_rate(
                        parameters_schema=CBRKeyRateParametersSchema(
                            start_time=input_schema.start_time,
                            end_time=input_schema.end_time,
                        )
                    )
                ),
                xpath=".//KR",
            )
        )
        interest_rates = interest_rates.select([col("DT").alias("timestamp"), col("Rate").alias("rate")])
        return (
            interest_rates.with_columns(
                lit(CBR).alias("bank"),
                lit(str(RUB)).alias("currency"),
                col("rate") / 100,
                col("timestamp").str.to_datetime(time_zone="UTC"),
            )
            .unique()
            .sort(by=col("timestamp"))
        )
