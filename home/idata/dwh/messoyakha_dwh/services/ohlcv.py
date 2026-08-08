from datetime import datetime

from attrs import define
from polars import DataFrame

from messoyakha_dwh.adapters.repositories.ohlcv import OHLCVS3Repository


@define(slots=True, auto_attribs=True, kw_only=True)
class OHLCVService:
    _repository: OHLCVS3Repository

    def load_to_dwh(
        self,
        data: DataFrame,
        path: str,
        partitions: list[str],
    ) -> None:
        self._repository._write(data=data, path=path, partition_columns=partitions)  # noqa: SLF001

    def query_latest_timestamp(
        self, ticker: str, venue: str, product: str, currency: str, interval: str
    ) -> datetime | None:
        return self._repository.query_latest_timestamp(
            ticker=ticker, venue=venue, product=product, currency=currency, interval=interval
        )
