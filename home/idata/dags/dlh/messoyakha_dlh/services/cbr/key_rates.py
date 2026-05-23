from datetime import datetime, timezone

from attrs import define
from polars import DataFrame
from that_depends import Provide, inject

from messoyakha_dlh.adapters.repositories.cbr.key_rates import CBRKeyRatesS3Repository
from messoyakha_dlh.settings import DLHSettings


class CBRKeyRatesDLHSettings(DLHSettings):
    CATCH_UP_DATE: datetime = datetime(year=2022, month=1, day=1, tzinfo=timezone.utc)


@define(slots=True, auto_attribs=True, kw_only=True)
class CBRKeyRatesDLHService:
    _repository: CBRKeyRatesS3Repository

    @inject
    def migrate_key_rates(self, settings: CBRKeyRatesDLHSettings = Provide["CBRKeyRatesContainer.settings"]) -> None:
        self._repository.migrate_key_rates(catalog=settings.catalog, namespace=settings.NAMESPACE)

    @inject
    def load_key_rates(
        self, key_rates: DataFrame, settings: CBRKeyRatesDLHSettings = Provide["CBRKeyRatesContainer.settings"]
    ) -> None:
        self._repository.load_key_rates(key_rates=key_rates, catalog=settings.catalog, namespace=settings.NAMESPACE)

    @inject
    def query_latest_timestamp(
        self, settings: CBRKeyRatesDLHSettings = Provide["CBRKeyRatesContainer.settings"]
    ) -> datetime:
        return self._repository.query_latest_timestamp(
            uri=settings.uri,
            catalog=settings.catalog,
            namespace=settings.NAMESPACE,
            catch_up_date=settings.CATCH_UP_DATE,
        )
