from datetime import datetime

from attrs import define
from polars import DataFrame

from messoyakha_dlh.adapters.repositories.dohod import DohodS3Repository


@define(slots=True, auto_attribs=True, kw_only=True)
class DohodDLHService:
    _repository: DohodS3Repository

    def truncate_dlh(self, path: str) -> None:
        self._repository._truncate(path=path)  # noqa: SLF001

    def load_to_dlh(
        self,
        data: DataFrame,
        path: str,
        partitions: list[str],
    ) -> None:
        self._repository._write(data=data, path=path, partition_columns=partitions)  # noqa: SLF001

    def query_dividends(self, ticker: str, venue: str, currency: str, since_date: datetime | None) -> DataFrame:
        if since_date:
            return self._repository.query_dividends_since_date(
                ticker=ticker, venue=venue, currency=currency, since_date=since_date
            )
        return self._repository.query_dividends(ticker=ticker, venue=venue, currency=currency)
