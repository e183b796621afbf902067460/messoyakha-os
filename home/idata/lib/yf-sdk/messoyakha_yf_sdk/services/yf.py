from asyncio import sleep
from datetime import datetime

from attrs import define, field
from polars import DataFrame, col, from_pandas, lit

from messoyakha_yf_sdk.adapters.yf import YFAPIClient
from messoyakha_yf_sdk.schemas.history import YFHistoryInputSchema
from messoyakha_yf_sdk.schemas.history_min_date import YFHistoryMinDateInputSchema


@define(slots=True, auto_attribs=True, kw_only=True)
class YFService:
    _client: YFAPIClient = field(init=False, factory=YFAPIClient)

    async def get_ohlcv(self, input_schema: YFHistoryInputSchema) -> DataFrame:
        data: DataFrame = (
            from_pandas(self._client.history(input_schema=input_schema))
            .with_columns(
                ticker=lit(input_schema.ticker),
                interval=lit(input_schema.interval.value),
                product=lit(input_schema.product),
                venue=lit(input_schema.venue),
                currency=lit(input_schema.currency),
            )
            .unique()
            .sort(by=col("timestamp"))
        )
        await sleep(1)
        return data

    async def get_first_trade_date(self, input_schema: YFHistoryMinDateInputSchema) -> datetime:
        first_trade_date: datetime = self._client.history_min_date(ticker=input_schema.ticker)
        await sleep(1)
        return first_trade_date
