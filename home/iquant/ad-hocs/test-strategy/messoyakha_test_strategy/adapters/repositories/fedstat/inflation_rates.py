from attr import define, field
from polars import DataFrame, scan_iceberg
from pyiceberg.catalog import Catalog

from messoyakha_coupling.adapters.repositories.s3 import S3PolarsRepositoryBase


@define(slots=True, auto_attribs=True, kw_only=True)
class FedstatInflationRatesS3Repository(S3PolarsRepositoryBase):
    _namespace: str = field(init=False, default="fedstat")
    _table: str = field(init=False, default="inflation-rates")

    def read_inflation_rates(self, catalog: Catalog, namespace: str) -> DataFrame:
        self._context.register(
            name="inflation_rates",
            frame=scan_iceberg(
                source=catalog.load_table(identifier=(namespace, self._namespace, self._table)),
                storage_options=self._options,
            ),
        )
        query: str = """
            SELECT
                inflation_rate,
                timestamp
            FROM
                inflation_rates
            ORDER BY
                timestamp
        """
        return self._query(query=query).collect()
