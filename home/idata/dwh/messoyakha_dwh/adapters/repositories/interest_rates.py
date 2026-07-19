from datetime import datetime, timezone

from attr import define
from polars.exceptions import ComputeError

from messoyakha_sdk.adapters.repositories.s3 import S3PolarsRepositoryBase
from messoyakha_sdk.decorators.route import path_route as route


@define(slots=False, auto_attribs=True, kw_only=True)
class InterestRatesS3Repository(S3PolarsRepositoryBase):
    @route(table="interest_rates", path="54bb0ca3-5204-4d58-ad1b-3a731de6a032/interest-rates/**/*.parquet")
    def query_bank_latest_timestamp(self, bank: str) -> datetime | None:
        query: str = f"""
            SELECT
                MAX(timestamp) AS timestamp
            FROM
                interest_rates
            WHERE
                bank = {bank!r}
        """
        latest_timestamp: datetime | None = None
        try:
            query_result: datetime = self._query(query=query).collect().item(row=0, column="timestamp")
        except ComputeError:
            return latest_timestamp
        return query_result.replace(tzinfo=timezone.utc)
