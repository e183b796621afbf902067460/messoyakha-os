from datetime import datetime, timezone

from attr import define
from polars.exceptions import ComputeError

from messoyakha_sdk.adapters.repositories.s3 import S3PolarsRepositoryBase
from messoyakha_sdk.decorators.route import path_route as route


@define(slots=False, auto_attribs=True, kw_only=True)
class MOEXISSS3Repository(S3PolarsRepositoryBase):
    @route(table="ohlcv", path="f8e90488-f511555d-274b-4258-bffc-572dd1900382/moex-iss/ohlcv/**/*.parquet")
    def query_latest_ohlcv_timestamp(
        self, ticker: str, venue: str, product: str, currency: str, interval: int
    ) -> datetime | None:
        query: str = f"""
            SELECT
                MAX(timestamp) AS timestamp
            FROM
                ohlcv
            WHERE
                _partition_by_ticker = {ticker!r}
                AND _partition_by_interval = {interval}
                AND _partition_by_product = {product!r}
                AND _partition_by_venue = {venue!r}
                AND _partition_by_currency = {currency!r}
        """

        latest_timestamp: datetime | None = None
        try:
            query_result: datetime = self._query(query=query).collect().item(row=0, column="timestamp")
        except ComputeError:
            return latest_timestamp
        return query_result.replace(tzinfo=timezone.utc)
