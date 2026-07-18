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
