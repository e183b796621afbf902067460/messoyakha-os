from datetime import datetime, timezone

from attr import define
from polars.exceptions import ComputeError

from messoyakha_sdk.adapters.repositories.s3 import S3PolarsRepositoryBase
from messoyakha_sdk.decorators.route import path_route as route


@define(slots=False, auto_attribs=True, kw_only=True)
class OHLCVS3Repository(S3PolarsRepositoryBase):
    @route(table="ohlcv", path="54bb0ca3-5204-4d58-ad1b-3a731de6a032/ohlcv/**/*.parquet")
    def query_latest_timestamp(
        self, ticker: str, interval: str, product: str, venue: str, currency: str
    ) -> datetime | None:
        query: str = f"""
            SELECT
                MAX(timestamp) AS timestamp
            FROM
                ohlcv
            WHERE
                _partition_by_ticker = {ticker!r}
                AND _partition_by_interval = {interval!r}
                AND _partition_by_product = {product!r}
                AND _partition_by_venue = {venue!r}
                AND _partition_by_currency = {currency!r}
        """
        latest_timestamp: datetime | None = None
        try:
            query_result: datetime | None = self._query(query=query).collect().item(row=0, column="timestamp")
        except ComputeError:
            return latest_timestamp
        return query_result.replace(tzinfo=timezone.utc) if query_result else latest_timestamp
