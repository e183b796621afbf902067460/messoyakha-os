from datetime import datetime

from attrs import define
from pandas import DataFrame
from yfinance import Ticker

from messoyakha_yf_sdk.schemas.history import YFHistoryInputSchema


@define(slots=True, auto_attribs=True, kw_only=True)
class YFAPIClient:
    def history(self, input_schema: YFHistoryInputSchema) -> DataFrame:
        return (
            Ticker(input_schema.ticker)
            .history(
                start=input_schema.start_time,
                end=input_schema.end_time,
                interval=input_schema.interval.value,
                auto_adjust=True,
                actions=False,
            )
            .rename(columns=str.lower)
            .reset_index(names="timestamp")[["timestamp", "open", "high", "low", "close", "volume"]]
        )

    def history_min_date(self, ticker: str) -> datetime:
        history: DataFrame = Ticker(ticker).history(period="max", auto_adjust=True, actions=False)
        return history.index.min().to_pydatetime()
