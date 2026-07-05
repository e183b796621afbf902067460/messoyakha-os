from datetime import datetime, timezone

from attrs import define
from polars import DataFrame
from that_depends import Provide, inject

from messoyakha_finam_sdk.enums.intervals import FinamIntervalEnum
from messoyakha_finam_sdk.enums.markets import FinamMarketEnum

from messoyakha_dlh.adapters.repositories.finam.ohlcv import FinamOHLCVS3Repository
from messoyakha_dlh.settings import DLHSettings


class FinamOHLCVDLHSettings(DLHSettings):
    CATCH_UP_DATE: datetime = datetime(year=2011, month=1, day=1, tzinfo=timezone.utc)
    TICKERS: list[tuple[str, FinamMarketEnum, FinamIntervalEnum]] = [
        ("SIBN", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("GAZP", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("ROSN", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("NVTK", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("TRNFP", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("PHOR", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("PLZL", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
        ("SBER", FinamMarketEnum.MISX, FinamIntervalEnum.ONE_DAY),
    ]

    FINAM_SECRET: str


@define(slots=True, auto_attribs=True, kw_only=True)
class FinamOHLCVDLHService:
    _repository: FinamOHLCVS3Repository

    @inject
    def migrate_ohlcv(self, settings: FinamOHLCVDLHSettings = Provide["FinamOHLCVContainer.settings"]) -> None:
        self._repository.migrate_ohlcv(catalog=settings.catalog, namespace=settings.NAMESPACE)

    @inject
    def load_ohlcv(
        self, ohlcv: DataFrame, settings: FinamOHLCVDLHSettings = Provide["FinamOHLCVContainer.settings"]
    ) -> None:
        self._repository.load_ohlcv(ohlcv=ohlcv, catalog=settings.catalog, namespace=settings.NAMESPACE)

    @inject
    def query_latest_timestamp(
        self,
        ticker: str,
        market: FinamMarketEnum,
        interval: FinamIntervalEnum,
        settings: FinamOHLCVDLHSettings = Provide["FinamOHLCVContainer.settings"],
    ) -> datetime:
        return self._repository.query_latest_timestamp(
            catalog=settings.catalog,
            namespace=settings.NAMESPACE,
            ticker=ticker,
            market=market.value,
            interval=interval.value,
            catch_up_date=settings.CATCH_UP_DATE,
        )
