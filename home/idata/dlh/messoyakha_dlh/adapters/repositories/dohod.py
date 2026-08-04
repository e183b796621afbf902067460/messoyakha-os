from datetime import datetime

from attr import define
from polars import DataFrame
from polars.exceptions import ComputeError

from messoyakha_sdk.adapters.repositories.s3 import S3PolarsRepositoryBase
from messoyakha_sdk.decorators.route import path_route as route


@define(slots=False, auto_attribs=True, kw_only=True)
class DohodS3Repository(S3PolarsRepositoryBase):
    @route(table="dividends", path="f8e90488-f511555d-274b-4258-bffc-572dd1900382/dohod/dividends/**/*.parquet")
    def query_dividends(self, ticker: str, venue: str, currency: str) -> DataFrame:
        query: str = f"""
            SELECT
                dividend,
                _partition_by_ticker AS ticker,
                _partition_by_venue AS venue,
                _partition_by_currency AS currency,
                timestamp
            FROM
                dividends
            WHERE
                _partition_by_ticker = {ticker!r}
                AND _partition_by_venue = {venue!r}
                AND _partition_by_currency = {currency!r}
        """
        try:
            return self._query(query=query).collect()
        except ComputeError as error:
            raise FileNotFoundError("There is no data for dividends.") from error

    @route(table="dividends", path="f8e90488-f511555d-274b-4258-bffc-572dd1900382/dohod/dividends/**/*.parquet")
    def query_dividends_since_date(self, ticker: str, venue: str, currency: str, since_date: datetime) -> DataFrame:
        query: str = f"""
            SELECT
                dividend,
                _partition_by_ticker AS ticker,
                _partition_by_venue AS venue,
                _partition_by_currency AS currency,
                timestamp
            FROM
                dividends
            WHERE
                _partition_by_ticker = {ticker!r}
                AND _partition_by_venue = {venue!r}
                AND _partition_by_currency = {currency!r}
                AND CAST(timestamp AS DATE) > {since_date.date().isoformat()!r}
        """
        try:
            return self._query(query=query).collect()
        except ComputeError as error:
            raise FileNotFoundError("There is no data for dividends.") from error
