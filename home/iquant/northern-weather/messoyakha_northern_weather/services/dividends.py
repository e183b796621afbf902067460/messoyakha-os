from attrs import define
from polars import DataFrame

from messoyakha_northern_weather.adapters.dividends import DividendsS3Repository


@define(slots=True, auto_attribs=True, kw_only=True)
class DividendsService:
    _repository: DividendsS3Repository

    def query_dividends(self, ticker: str, venue: str, currency: str) -> DataFrame:
        return self._repository.query_dividends(ticker=ticker, venue=venue, currency=currency)
