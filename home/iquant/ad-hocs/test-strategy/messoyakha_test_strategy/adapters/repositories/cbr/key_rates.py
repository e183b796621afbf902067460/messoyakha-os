from attr import define, field
from polars import DataFrame, scan_iceberg
from pyiceberg.catalog import Catalog

from messoyakha_coupling.adapters.repositories.s3 import S3PolarsRepositoryBase


@define(slots=True, auto_attribs=True, kw_only=True)
class CBRKeyRatesS3Repository(S3PolarsRepositoryBase):
    _namespace: str = field(init=False, default="cbr")
    _table: str = field(init=False, default="key-rates")

    def read_key_rates(self, catalog: Catalog, namespace: str) -> DataFrame:
        self._context.register(
            name="key_rates",
            frame=scan_iceberg(
                source=catalog.load_table(identifier=(namespace, self._namespace, self._table)),
                storage_options=self._options,
            ),
        )
        query: str = """
            SELECT
                key_rate,
                timestamp
            FROM
                key_rates
            ORDER BY
                timestamp
        """
        return self._query(query=query).collect()
