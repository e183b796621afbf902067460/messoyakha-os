from datetime import datetime, timezone

from attrs import define
from polars import DataFrame
from that_depends import Provide, inject

from messoyakha_dlh.adapters.repositories.fedstat.inflation_rates import FedstatInflationRatesS3Repository
from messoyakha_dlh.settings import DLHSettings


class FedstatInflationRatesDLHSettings(DLHSettings):
    CATCH_UP_DATE: datetime = datetime(year=2003, month=1, day=1, tzinfo=timezone.utc)


@define(slots=True, auto_attribs=True, kw_only=True)
class FedstatInflationRatesDLHService:
    _repository: FedstatInflationRatesS3Repository

    @inject
    def migrate_inflation_rates(
        self, settings: FedstatInflationRatesDLHSettings = Provide["FedstatInflationRatesContainer.settings"]
    ) -> None:
        self._repository.migrate_inflation_rates(catalog=settings.catalog, namespace=settings.NAMESPACE)

    @inject
    def load_inflation_rates(
        self,
        inflation_rates: DataFrame,
        settings: FedstatInflationRatesDLHSettings = Provide["FedstatInflationRatesContainer.settings"],
    ) -> None:
        self._repository.load_inflation_rates(
            inflation_rates=inflation_rates, catalog=settings.catalog, namespace=settings.NAMESPACE
        )

    @inject
    def query_latest_timestamp(
        self, settings: FedstatInflationRatesDLHSettings = Provide["FedstatInflationRatesContainer.settings"]
    ) -> datetime:
        return self._repository.query_latest_timestamp(
            catalog=settings.catalog,
            namespace=settings.NAMESPACE,
            catch_up_date=settings.CATCH_UP_DATE,
        )
