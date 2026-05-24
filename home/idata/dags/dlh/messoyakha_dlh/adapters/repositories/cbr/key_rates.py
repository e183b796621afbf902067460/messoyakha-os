from datetime import datetime

from attr import define, field
from polars import DataFrame
from pyiceberg.catalog import Catalog
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import NestedField, Schema
from pyiceberg.transforms import DayTransform
from pyiceberg.types import DoubleType, TimestamptzType

from messoyakha_coupling.adapters.repositories.s3 import DuckDBIcebergS3RepositoryBase


@define(slots=True, auto_attribs=True, kw_only=True)
class CBRKeyRatesS3Repository(DuckDBIcebergS3RepositoryBase):
    _namespace: str = field(init=False, default="cbr")
    _table: str = field(init=False, default="key-rates")

    def _v1(self, catalog: Catalog, namespace: str) -> None:
        catalog.create_namespace_if_not_exists(namespace=(namespace, self._namespace))
        if catalog.namespace_exists(namespace=(namespace, self._namespace)):
            catalog.create_table_if_not_exists(
                identifier=(namespace, self._namespace, self._table),
                schema=Schema(
                    NestedField(field_id=1, name="key_rate", field_type=DoubleType()),  # type: ignore[missing-argument]
                    NestedField(field_id=2, name="timestamp", field_type=TimestamptzType()),  # type: ignore[missing-argument]
                ),
                partition_spec=PartitionSpec(
                    PartitionField(
                        source_id=2,
                        field_id=1000,
                        transform=DayTransform(),  # type: ignore[missing-argument]
                        name="_partition_by_timestamp",
                    ),
                ),
            )

    def migrate_key_rates(self, catalog: Catalog, namespace: str) -> None:
        self._v1(namespace=namespace, catalog=catalog)

    def load_key_rates(self, key_rates: DataFrame, catalog: Catalog, namespace: str) -> None:
        if catalog.table_exists(identifier=(namespace, self._namespace, self._table)):
            key_rates.write_iceberg(
                target=catalog.load_table(identifier=(namespace, self._namespace, self._table)),
                mode="append",
            )

    def query_latest_timestamp(self, uri: str, catalog: Catalog, namespace: str, catch_up_date: datetime) -> datetime:
        if catalog.table_exists(identifier=(namespace, self._namespace, self._table)):
            query: str = f"""
                SELECT
                    MAX(timestamp)
                FROM
                    iceberg_scan('{uri}/{namespace}/{self._namespace}/{self._table}')
            """
            return self._query(query=query)
        return catch_up_date
