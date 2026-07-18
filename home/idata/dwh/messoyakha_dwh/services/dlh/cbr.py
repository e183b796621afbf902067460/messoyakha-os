from datetime import datetime

from attrs import define
from polars import DataFrame

from messoyakha_dlh.adapters.repositories.cbr import CBRS3Repository


@define(slots=True, auto_attribs=True, kw_only=True)
class CBRDLHService:
    _repository: CBRS3Repository

    def load_to_dlh(
        self,
        data: DataFrame,
        path: str,
        partitions: list[str],
    ) -> None:
        self._repository._write(data=data, path=path, partition_columns=partitions)  # noqa: SLF001

    def query_latest_interest_rate_timestamp(self) -> datetime | None:
        return self._repository.query_latest_interest_rate_timestamp()
