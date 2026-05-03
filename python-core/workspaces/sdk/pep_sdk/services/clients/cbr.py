from io import BytesIO

from attrs import define, field
from pandas import read_xml
from polars import DataFrame, col, from_pandas

from pep_sdk.adapters.clients.cbr import CBRSOAPAPIClient
from pep_sdk.schemas.clients.cbr import CBRKeyRateParametersSchema


@define(slots=True, auto_attribs=True, kw_only=True)
class CBRService:
    _client: CBRSOAPAPIClient = field(init=False, factory=CBRSOAPAPIClient)

    def get_key_rate(self, parameters_schema: CBRKeyRateParametersSchema) -> DataFrame:
        key_rate: DataFrame = from_pandas(
            read_xml(BytesIO(self._client.key_rate(parameters_schema=parameters_schema)), xpath=".//KR")
        )
        key_rate = key_rate.select([col("DT").alias("datetime"), col("Rate").alias("key_rate")])
        return (
            key_rate.with_columns(col("datetime").str.to_datetime().dt.replace_time_zone("UTC"), col("key_rate") / 100)
            .unique()
            .sort(by=col("datetime"))
        )
