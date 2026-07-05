from attrs import define
from polars import DataFrame
from that_depends import Provide, inject

from messoyakha_dlh.adapters.repositories.dohod.dividends import DohodDividendsS3Repository
from messoyakha_dlh.settings import DLHSettings


class DohodDividendsDLHSettings(DLHSettings):
    TICKERS: list[str] = [
        "SIBN",
        "ROSN",
        "NVTK",
        "TRNFP",
        "PHOR",
        "PLZL",
        "SBER",
    ]


@define(slots=True, auto_attribs=True, kw_only=True)
class DohodDividendsDLHService:
    _repository: DohodDividendsS3Repository

    @inject
    def migrate_dividends(
        self, settings: DohodDividendsDLHSettings = Provide["DohodDividendsContainer.settings"]
    ) -> None:
        self._repository.migrate_dividends(catalog=settings.catalog, namespace=settings.NAMESPACE)

    @inject
    def load_dividends(
        self, dividends: DataFrame, settings: DohodDividendsDLHSettings = Provide["DohodDividendsContainer.settings"]
    ) -> None:
        self._repository.load_dividends(dividends=dividends, catalog=settings.catalog, namespace=settings.NAMESPACE)
