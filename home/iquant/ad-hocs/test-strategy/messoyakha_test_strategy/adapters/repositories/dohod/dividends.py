from attr import define, field
from polars import DataFrame, scan_iceberg
from pyiceberg.catalog import Catalog

from messoyakha_coupling.adapters.repositories.s3 import S3PolarsRepositoryBase


@define(slots=True, auto_attribs=True, kw_only=True)
class DohodDividendsS3Repository(S3PolarsRepositoryBase):
    _namespace: str = field(init=False, default="dohod")
    _table: str = field(init=False, default="dividends")

    def read_dividends(self, catalog: Catalog, namespace: str, ticker: str) -> DataFrame:
        self._context.register(
            name="dividends",
            frame=scan_iceberg(
                source=catalog.load_table(identifier=(namespace, self._namespace, self._table)),
                storage_options=self._options,
            ),
        )
        query: str = f"""
            SELECT
                ticker,
                dividend,
                timestamp
            FROM
                dividends
            WHERE
                ticker = {ticker!r}
            ORDER BY
                timestamp
        """
        return self._query(query=query).collect()
