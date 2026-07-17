from datetime import datetime, timezone

from attr import define
from polars.exceptions import ComputeError

from messoyakha_sdk.adapters.repositories.s3 import S3PolarsRepositoryBase
from messoyakha_sdk.decorators.route import path_route as route


@define(slots=False, auto_attribs=True, kw_only=True)
class CBRS3Repository(S3PolarsRepositoryBase):
    @route(table="interest_rates", path="f8e90488-f511555d-274b-4258-bffc-572dd1900382/cbr/interest-rates/**/*.parquet")
    def query_latest_interest_rate_timestamp(self) -> datetime | None:
        query: str = """
            SELECT
                MAX(timestamp) AS timestamp
            FROM
                interest_rates
        """

        latest_timestamp: datetime | None = None
        try:
            query_result: str | None = self._query(query=query).collect().item(row=0, column="timestamp")
        except ComputeError:
            return latest_timestamp
        return datetime.fromisoformat(query_result).replace(tzinfo=timezone.utc) if query_result else latest_timestamp
