from datetime import datetime

from attrs import define
from polars import DataFrame

from messoyakha_dwh.adapters.repositories.interest_rates import InterestRatesS3Repository


@define(slots=True, auto_attribs=True, kw_only=True)
class InterestRatesService:
    _repository: InterestRatesS3Repository

    def load_to_dwh(
        self,
        data: DataFrame,
        path: str,
        partitions: list[str],
    ) -> None:
        self._repository._write(data=data, path=path, partition_columns=partitions)  # noqa: SLF001

    def query_bank_latest_timestamp(self, bank: str) -> datetime | None:
        return self._repository.query_bank_latest_timestamp(bank=bank)
