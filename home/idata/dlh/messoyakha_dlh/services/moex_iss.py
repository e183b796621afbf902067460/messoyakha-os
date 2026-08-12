from datetime import datetime

from attrs import define
from polars import DataFrame

from messoyakha_moex_iss_sdk.enums.intervals import MOEXIntervalEnum

from messoyakha_dlh.adapters.repositories.moex_iss import MOEXISSS3Repository


@define(slots=True, auto_attribs=True, kw_only=True)
class MOEXISSDLHService:
    _repository: MOEXISSS3Repository

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
        interval: MOEXIntervalEnum,
        product: str,
        venue: str,
        currency: str,
    ) -> datetime | None:
        return self._repository.query_latest_ohlcv_timestamp(
            ticker=ticker,
            interval=interval.value,
            product=product,
            venue=venue,
            currency=currency,
        )

    def query_ohlcv(
        self,
        ticker: str,
        interval: MOEXIntervalEnum,
        product: str,
        venue: str,
        currency: str,
        since_date: datetime | None,
    ) -> DataFrame:
        if since_date:
            return self._repository.query_ohlcv_since_date(
                ticker=ticker,
                venue=venue,
                product=product,
                currency=currency,
                interval=interval.value,
                since_date=since_date,
            )
        return self._repository.query_ohlcv(
            ticker=ticker,
            venue=venue,
            product=product,
            currency=currency,
            interval=interval.value,
        )
