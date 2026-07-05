from datetime import datetime, timezone

from attr import define, field
from polars import DataFrame, scan_iceberg
from pyiceberg.catalog import Catalog
from pyiceberg.partitioning import DayTransform, IdentityTransform, PartitionField, PartitionSpec
from pyiceberg.schema import NestedField, Schema
from pyiceberg.types import DoubleType, StringType, TimestamptzType

from messoyakha_coupling.adapters.repositories.s3 import S3PolarsRepositoryBase


@define(slots=True, auto_attribs=True, kw_only=True)
class FinamOHLCVS3Repository(S3PolarsRepositoryBase):
    _namespace: str = field(init=False, default="finam")
    _table: str = field(init=False, default="ohlcv")

    def _v1(self, catalog: Catalog, namespace: str) -> None:
        catalog.create_namespace_if_not_exists(namespace=(namespace, self._namespace))
        if catalog.namespace_exists(identifier=(namespace, self._namespace)):  # type: ignore[unexpected-keyword, missing-argument]
            catalog.create_table_if_not_exists(
                identifier=(namespace, self._namespace, self._table),
                schema=Schema(
                    NestedField(field_id=1, name="ticker", field_type=StringType()),  # type: ignore[missing-argument]
                    NestedField(field_id=2, name="market", field_type=StringType()),  # type: ignore[missing-argument]
                    NestedField(field_id=3, name="interval", field_type=StringType()),  # type: ignore[missing-argument]
                    NestedField(field_id=4, name="open", field_type=DoubleType()),  # type: ignore[missing-argument]
                    NestedField(field_id=5, name="high", field_type=DoubleType()),  # type: ignore[missing-argument]
                    NestedField(field_id=6, name="low", field_type=DoubleType()),  # type: ignore[missing-argument]
                    NestedField(field_id=7, name="close", field_type=DoubleType()),  # type: ignore[missing-argument]
                    NestedField(field_id=8, name="volume", field_type=DoubleType()),  # type: ignore[missing-argument]
                    NestedField(field_id=9, name="timestamp", field_type=TimestamptzType()),  # type: ignore[missing-argument]
                ),
                partition_spec=PartitionSpec(
                    PartitionField(
                        source_id=1, field_id=1000, transform=IdentityTransform(), name="_partition_by_ticker"
                    ),
                    PartitionField(
                        source_id=2, field_id=1001, transform=IdentityTransform(), name="_partition_by_market"
                    ),
                    PartitionField(
                        source_id=3, field_id=1002, transform=IdentityTransform(), name="_partition_by_interval"
                    ),
                    PartitionField(
                        source_id=9,
                        field_id=1003,
                        transform=DayTransform(),  # type: ignore[missing-argument]
                        name="_partition_by_timestamp",
                    ),
                ),
            )

    def migrate_ohlcv(self, catalog: Catalog, namespace: str) -> None:
        self._v1(namespace=namespace, catalog=catalog)

    def load_ohlcv(self, ohlcv: DataFrame, catalog: Catalog, namespace: str) -> None:
        if catalog.table_exists(identifier=(namespace, self._namespace, self._table)):
            ohlcv.write_iceberg(
                target=catalog.load_table(identifier=(namespace, self._namespace, self._table)),
                mode="append",
            )

    def query_latest_timestamp(
        self,
        catalog: Catalog,
        namespace: str,
        ticker: str,
        market: str,
        interval: str,
        catch_up_date: datetime,
    ) -> datetime:
        self._context.register(
            name="ohlcv",
            frame=scan_iceberg(
                source=catalog.load_table(identifier=(namespace, self._namespace, self._table)),
                storage_options=self._options,
            ),
        )
        query: str = f"""
            SELECT
                COALESCE(MAX(timestamp), {str(catch_up_date)!r})
            FROM
                ohlcv
            WHERE
                ticker = {ticker!r}
                AND market = {market!r}
                AND `interval` = {interval!r}
        """
        query_result: str = self._query(query=query).collect().item(row=0, column="timestamp")
        latest_timestamp: datetime = datetime.fromisoformat(query_result).replace(tzinfo=timezone.utc)
        return latest_timestamp
