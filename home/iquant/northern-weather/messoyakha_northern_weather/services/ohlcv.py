from attrs import define
from polars import DataFrame

from messoyakha_sdk.enums.intervals import MessoyakhaIntervalEnum

from messoyakha_northern_weather.adapters.ohlcv import OHLCVS3Repository


@define(slots=True, auto_attribs=True, kw_only=True)
class OHLCVService:
    _repository: OHLCVS3Repository

    def query_ohlcv(
        self, ticker: str, interval: MessoyakhaIntervalEnum, product: str, venue: str, currency: str
    ) -> DataFrame:
        return self._repository.query_ohlcv(
            ticker=ticker, interval=interval.value, product=product, venue=venue, currency=currency
        )
