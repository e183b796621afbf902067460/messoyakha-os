from datetime import datetime

from attrs import define
from polars import DataFrame

from messoyakha_finam_sdk.enums.intervals import FinamIntervalEnum

from messoyakha_dlh.adapters.repositories.finam import FinamS3Repository


@define(slots=True, auto_attribs=True, kw_only=True)
class FinamDLHService:
    _repository: FinamS3Repository

    def load_to_dlh(
        self,
        data: DataFrame,
        path: str,
        partitions: list[str],
    ) -> None:
        self._repository._write(data=data, path=path, partition_columns=partitions)  # noqa: SLF001

    def query_latest_ohlcv_timestamp(
        self,
        ticker: str,
        interval: FinamIntervalEnum,
        product: str,
        venue: str,
        currency: str,
    ) -> datetime | None:
        return self._repository.query_latest_ohlcv_timestamp(
            ticker=ticker,
            venue=venue,
            product=product,
            currency=currency,
            interval=interval.value,
        )
