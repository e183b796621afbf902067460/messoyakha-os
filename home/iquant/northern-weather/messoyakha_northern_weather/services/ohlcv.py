from attrs import define
from polars import DataFrame

from messoyakha_northern_weather.adapters.ohlcv import OHLCVS3Repository


@define(slots=True, auto_attribs=True, kw_only=True)
class OHLCVService:
    _repository: OHLCVS3Repository

    def query_ohlcv(self, ticker: str, venue: str, product: str, currency: str, interval: str) -> DataFrame:
        return self._repository.query_ohlcv(
            ticker=ticker, venue=venue, product=product, currency=currency, interval=interval
        )
