from attr import define, field
from polars import DataFrame, scan_iceberg
from pyiceberg.catalog import Catalog

from messoyakha_coupling.adapters.repositories.s3 import S3PolarsRepositoryBase


@define(slots=True, auto_attribs=True, kw_only=True)
class FinamOHLCVS3Repository(S3PolarsRepositoryBase):
    _namespace: str = field(init=False, default="finam")
    _table: str = field(init=False, default="ohlcv")

    def read_ohlcv(self, catalog: Catalog, namespace: str, ticker: str, market: str, interval: str) -> DataFrame:
        self._context.register(
            name="ohlcv",
            frame=scan_iceberg(
                source=catalog.load_table(identifier=(namespace, self._namespace, self._table)),
                storage_options=self._options,
            ),
        )
        query: str = f"""
            SELECT
                ticker,
                market,
                `interval`,
                open,
                high,
                low,
                close,
                volume,
                timestamp
            FROM
                ohlcv
            WHERE
                ticker = {ticker!r}
                AND market = {market!r}
                AND `interval` = {interval!r}
            ORDER BY
                timestamp
        """
        return self._query(query=query).collect()
