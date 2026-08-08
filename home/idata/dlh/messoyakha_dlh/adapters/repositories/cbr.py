from datetime import datetime, timezone

from attr import define
from polars import DataFrame
from polars.exceptions import ComputeError

from messoyakha_sdk.adapters.repositories.s3 import S3PolarsRepositoryBase
from messoyakha_sdk.decorators.route import path_route as route


@define(slots=False, auto_attribs=True, kw_only=True)
class CBRS3Repository(S3PolarsRepositoryBase):
    @route(table="interest_rates", path="f8e90488-f511555d-274b-4258-bffc-572dd1900382/cbr/interest-rates/**/*.parquet")
    def query_latest_interest_rates_timestamp(self) -> datetime | None:
        query: str = """
            SELECT
                MAX(timestamp) AS timestamp
            FROM
                interest_rates
        """
        latest_timestamp: datetime | None = None
        try:
            query_result: datetime | None = self._query(query=query).collect().item(row=0, column="timestamp")
        except ComputeError:
            return latest_timestamp
        return query_result.replace(tzinfo=timezone.utc) if query_result else latest_timestamp

    @route(table="interest_rates", path="f8e90488-f511555d-274b-4258-bffc-572dd1900382/cbr/interest-rates/**/*.parquet")
    def query_interest_rates(self) -> DataFrame:
        query: str = """
            SELECT
                rate,
                bank,
                currency,
                timestamp
            FROM
                interest_rates
        """
        try:
            return self._query(query=query).collect()
        except ComputeError as error:
            raise FileNotFoundError("There is no data for CBR interest rates.") from error

    @route(table="interest_rates", path="f8e90488-f511555d-274b-4258-bffc-572dd1900382/cbr/interest-rates/**/*.parquet")
    def query_interest_rates_since_date(self, since_date: datetime) -> DataFrame:
        query: str = f"""
            SELECT
                rate,
                bank,
                currency,
                timestamp
            FROM
                interest_rates
            WHERE
                CAST(timestamp AS DATE) > {since_date.date().isoformat()!r}
        """
        try:
            return self._query(query=query).collect()
        except ComputeError as error:
            raise FileNotFoundError("There is no data for CBR interest rates.") from error
