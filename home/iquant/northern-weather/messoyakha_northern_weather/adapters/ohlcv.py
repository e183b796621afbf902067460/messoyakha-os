from attr import define
from polars import DataFrame
from polars.exceptions import ComputeError

from messoyakha_sdk.adapters.repositories.s3 import S3PolarsRepositoryBase
from messoyakha_sdk.decorators.route import path_route as route


@define(slots=False, auto_attribs=True, kw_only=True)
class OHLCVS3Repository(S3PolarsRepositoryBase):
    @route(table="ohlcv", path="54bb0ca3-5204-4d58-ad1b-3a731de6a032/ohlcv/**/*.parquet")
    def query_ohlcv(self, ticker: str, interval: str, product: str, venue: str, currency: str) -> DataFrame:
        query: str = f"""
            SELECT
                open,
                high,
                low,
                close,
                volume,
                _partition_by_ticker AS ticker,
                _partition_by_interval AS interval,
                _partition_by_product AS product,
                _partition_by_venue AS venue,
                _partition_by_currency AS currency,
                timestamp
            FROM
                ohlcv
            WHERE
                _partition_by_ticker = {ticker!r}
                AND _partition_by_interval = {interval!r}
                AND _partition_by_product = {product!r}
                AND _partition_by_venue = {venue!r}
                AND _partition_by_currency = {currency!r}
            ORDER BY
                timestamp
        """
        try:
            return self._query(query=query).collect()
        except ComputeError as error:
            raise FileNotFoundError("There is no data for OHLCV.") from error
