from attr import define, field
from polars import DataFrame
from pyiceberg.catalog import Catalog
from pyiceberg.partitioning import DayTransform, IdentityTransform, PartitionField, PartitionSpec
from pyiceberg.schema import NestedField, Schema
from pyiceberg.types import DoubleType, StringType, TimestamptzType

from messoyakha_coupling.adapters.repositories.s3 import PolarsIcebergS3RepositoryBase


@define(slots=True, auto_attribs=True, kw_only=True)
class DohodDividendsS3Repository(PolarsIcebergS3RepositoryBase):
    _namespace: str = field(init=False, default="dohod")
    _table: str = field(init=False, default="dividends")

    def _v1(self, catalog: Catalog, namespace: str) -> None:
        catalog.create_namespace_if_not_exists(namespace=(namespace, self._namespace))
        if catalog.namespace_exists(identifier=(namespace, self._namespace)):  # type: ignore[unexpected-keyword, missing-argument]
            catalog.create_table_if_not_exists(
                identifier=(namespace, self._namespace, self._table),
                schema=Schema(
                    NestedField(field_id=1, name="ticker", field_type=StringType()),  # type: ignore[missing-argument]
                    NestedField(field_id=2, name="dividend", field_type=DoubleType()),  # type: ignore[missing-argument]
                    NestedField(field_id=3, name="timestamp", field_type=TimestamptzType()),  # type: ignore[missing-argument]
                ),
                partition_spec=PartitionSpec(
                    PartitionField(
                        source_id=1, field_id=1000, transform=IdentityTransform(), name="_partition_by_ticker"
                    ),
                    PartitionField(
                        source_id=3,
                        field_id=1001,
                        transform=DayTransform(),  # type: ignore[missing-argument]
                        name="_partition_by_timestamp",
                    ),
                ),
            )

    def migrate_dividends(self, catalog: Catalog, namespace: str) -> None:
        self._v1(namespace=namespace, catalog=catalog)

    def load_dividends(self, dividends: DataFrame, catalog: Catalog, namespace: str) -> None:
        if catalog.table_exists(identifier=(namespace, self._namespace, self._table)):
            dividends.write_iceberg(
                target=catalog.load_table(identifier=(namespace, self._namespace, self._table)),
                mode="overwrite",
            )
