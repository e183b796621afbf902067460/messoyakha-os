# pylint: disable=too-many-lines, invalid-name, duplicate-code
from datetime import datetime

from attr import attrs
from polars import DataFrame

from src.adapters.clients.s3 import S3Client
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.common.polars_base import PolarsBaseRepository
from src.schemas.domain.s3 import ListObjectsResponseSchema
from src.schemas.filters import (
    LatestTimestampPathParametersSchema,
    LatestTimestampQueryParametersSchema,
    OHLCPathParametersSchema,
    OHLCQueryParametersSchema,
    PathParametersBaseSchema,
    QueryParametersBaseSchema,
)

# pylint: enable=duplicate-code


def _format_s3_key(
    query_parameters: QueryParametersBaseSchema,
    directory: str,
    filename: str | None = None,
) -> str:
    key: str = (
        f"development/"
        f"data/"
        f"{directory}/"
        f"{query_parameters.ticker.lower()}/"
        f"{query_parameters.exchange.lower()}/"
        f"{query_parameters.section.lower()}/"
        f"{query_parameters.interval.lower()}"
    )
    if filename:
        key = (
            f"development/"
            f"data/"
            f"{directory}/"
            f"{query_parameters.ticker.lower()}/"
            f"{query_parameters.exchange.lower()}/"
            f"{query_parameters.section.lower()}/"
            f"{query_parameters.interval.lower()}/"
            f"{filename}"
        )
    return key


@attrs(slots=False, auto_attribs=True, kw_only=True)
class _S3BaseService:
    _s3_client: S3Client

    _repository: PolarsBaseRepository

    _query_parameters: QueryParametersBaseSchema
    _path_parameters: PathParametersBaseSchema

    def __attrs_post_init__(self) -> None:
        self._objects: ListObjectsResponseSchema = self._s3_client.list_objects(
            bucket=self._path_parameters.bucket,
            prefix=_format_s3_key(
                query_parameters=self._query_parameters,
                directory=self._path_parameters.directory,
            ),
        )
        self._path: str = (
            f"s3://"
            f"{self._path_parameters.bucket}"
            f"/development/"
            f"data/"
            f"{self._path_parameters.directory}/"
            f"{self._query_parameters.ticker.lower()}/"
            f"{self._query_parameters.exchange.lower()}/"
            f"{self._query_parameters.section.lower()}/"
            f"{self._query_parameters.interval.lower()}"
        )

    def delete_object(self) -> None:
        if self._objects.filename:
            self._s3_client.delete_object(
                bucket=self._path_parameters.bucket,
                key=_format_s3_key(
                    query_parameters=self._query_parameters,
                    directory=self._path_parameters.directory,
                    filename=self._objects.filename,
                ),
            )

    @property
    def _formatted_path(self) -> str:
        return f"{self._path}/{self._objects.filename}" if self._objects.filename else f"{self._path}/"  # noqa: WPS221


@attrs(slots=False, auto_attribs=True, kw_only=True)
class OHLCService(_S3BaseService):
    _repository: CandlesticksRepository

    _query_parameters: OHLCQueryParametersSchema | LatestTimestampQueryParametersSchema
    _path_parameters: OHLCPathParametersSchema | LatestTimestampPathParametersSchema

    def __attrs_post_init__(self) -> None:
        _S3BaseService.__attrs_post_init__(self=self)  # noqa: WPS204
        self._ohlc: DataFrame | None = self._repository.query_candlesticks(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )
        self._latest_timestamp: datetime | None = self._repository.query_latest_timestamp(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )
        if isinstance(self._ohlc, DataFrame):
            self._ohlc = self._ohlc.unique()

    @property
    def ohlc(self) -> DataFrame | None:
        return self._ohlc

    @property
    def latest_timestamp(self) -> datetime | None:
        return self._latest_timestamp

    def load_ohlc(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(  # noqa: WPS204
            dataframe=dataframe, key=f"{self._path}/{filename}"
        )
