from io import BytesIO

from attrs import define, field
from pandas import read_xml
from polars import DataFrame, col, from_pandas

from messoyakha_cbr_sdk.adapters.cbr import CBRSOAPAPIClient
from messoyakha_cbr_sdk.schemas.key_rate import CBRKeyRateParametersSchema


@define(slots=True, auto_attribs=True, kw_only=True)
class CBRService:
    _client: CBRSOAPAPIClient = field(init=False, factory=CBRSOAPAPIClient)

    def get_key_rates(self, parameters_schema: CBRKeyRateParametersSchema) -> DataFrame:
        key_rates: DataFrame = from_pandas(
            read_xml(BytesIO(self._client.key_rate(parameters_schema=parameters_schema)), xpath=".//KR")
        )
        key_rates = key_rates.select([col("DT").alias("timestamp"), col("Rate").alias("key_rate")])
        return (
            key_rates.with_columns(
                col("timestamp").str.to_datetime().dt.replace_time_zone("UTC"), col("key_rate") / 100
            )
            .unique()
            .sort(by=col("timestamp"))
        )
