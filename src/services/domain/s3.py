from datetime import datetime
from typing import Any

from attr import attr, attrs
from pandas import DataFrame

from src.adapters.clients.s3 import S3Client
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.common.duckdb_base import DuckDBBaseRepository
from src.adapters.repositories.indicators import (
    ADXRepository,
    AroonRepository,
    BinariesRepository,
    MARepository,
    StreaksRepository,
)
from src.adapters.repositories.trades import TradesRepository
from src.adapters.repositories.trials import SARTrialsRepository
from src.schemas.domain.s3 import GetObjectResponseSchema, ListObjectsResponseSchema
from src.schemas.filters import (
    ADXPathParametersSchema,
    ADXQueryParametersSchema,
    AroonPathParametersSchema,
    AroonQueryParametersSchema,
    BinaryPathParametersSchema,
    BinaryQueryParametersSchema,
    LatestTimestampPathParametersSchema,
    LatestTimestampQueryParametersSchema,
    MAPathParametersSchema,
    MAQueryParametersSchema,
    MLModelPathParametersSchema,
    MLModelQueryParametersSchema,
    OHLCPathParametersSchema,
    OHLCQueryParametersSchema,
    PathParametersBaseSchema,
    QueryParametersBaseSchema,
    SARTrialPathParametersSchema,
    SARTrialQueryParametersSchema,
    StreakPathParametersSchema,
    StreakQueryParametersSchema,
    TradePathParametersSchema,
    TradeQueryParametersSchema,
)


def _format_s3_key(query_parameters: QueryParametersBaseSchema, directory: str, filename: str | None = None) -> str:
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


@attrs(slots=True, auto_attribs=True, kw_only=True)
class _S3BaseService:

    _s3_client: S3Client

    _repository: DuckDBBaseRepository

    _query_parameters: QueryParametersBaseSchema
    _path_parameters: PathParametersBaseSchema

    def __attrs_post_init__(self) -> None:
        self._objects: ListObjectsResponseSchema = self._s3_client.list_objects(
            bucket=self._path_parameters.bucket,
            prefix=_format_s3_key(query_parameters=self._query_parameters, directory=self._path_parameters.directory),
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

    _objects: ListObjectsResponseSchema = attr(init=False)
    _path: str = attr(init=False)


class OHLCService(_S3BaseService):

    _repository: CandlesticksRepository

    _query_parameters: OHLCQueryParametersSchema | LatestTimestampQueryParametersSchema
    _path_parameters: OHLCPathParametersSchema | LatestTimestampPathParametersSchema

    def extract_ohlc(self) -> DataFrame | None:
        return self._repository.query_candlesticks(parameters_schema=self._query_parameters, path=self._formatted_path)

    def extract_latest_timestamp(self) -> datetime | None:
        return self._repository.query_latest_timestamp(  # type: ignore[no-any-return]
            parameters_schema=self._query_parameters, path=self._formatted_path
        )

    def load_ohlc(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")


class MAService(_S3BaseService):
    _repository: MARepository

    _query_parameters: MAQueryParametersSchema
    _path_parameters: MAPathParametersSchema

    def extract_ma(self) -> DataFrame | None:
        return self._repository.query_moving_averages(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )

    def load_ma(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")


class ADXService(_S3BaseService):
    _repository: ADXRepository

    _query_parameters: ADXQueryParametersSchema
    _path_parameters: ADXPathParametersSchema

    def extract_adx(self) -> DataFrame | None:
        return self._repository.query_average_directional_indexes(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )

    def load_adx(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")


class SARService(_S3BaseService):
    _repository: SARTrialsRepository

    _query_parameters: SARTrialQueryParametersSchema
    _path_parameters: SARTrialPathParametersSchema

    def extract_sar(self) -> DataFrame | None:
        return self._repository.query_stop_and_reverse_trials(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )

    def load_sar(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")


class ROIService(_S3BaseService):
    _repository: TradesRepository

    _query_parameters: TradeQueryParametersSchema
    _path_parameters: TradePathParametersSchema

    def extract_roi(self) -> DataFrame | None:
        return self._repository.query_trades(parameters_schema=self._query_parameters, path=self._formatted_path)

    def load_roi(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")


class AroonService(_S3BaseService):
    _repository: AroonRepository

    _query_parameters: AroonQueryParametersSchema
    _path_parameters: AroonPathParametersSchema

    def extract_aroon(self) -> DataFrame | None:
        return self._repository.query_aroons(parameters_schema=self._query_parameters, path=self._formatted_path)

    def load_aroon(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")


class BinaryService(_S3BaseService):
    _repository: BinariesRepository

    _query_parameters: BinaryQueryParametersSchema
    _path_parameters: BinaryPathParametersSchema

    def extract_binary(self) -> DataFrame | None:
        return self._repository.query_binaries(parameters_schema=self._query_parameters, path=self._formatted_path)

    def load_binary(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")


class StreakService(_S3BaseService):
    _repository: StreaksRepository

    _query_parameters: StreakQueryParametersSchema
    _path_parameters: StreakPathParametersSchema

    def extract_streak(self) -> DataFrame | None:
        return self._repository.query_streaks(parameters_schema=self._query_parameters, path=self._formatted_path)

    def load_streak(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")


@attrs(slots=True, auto_attribs=True, kw_only=True)
class MLModelService(_S3BaseService):

    _query_parameters: MLModelQueryParametersSchema
    _path_parameters: MLModelPathParametersSchema

    def extract_ml_model(self) -> GetObjectResponseSchema:
        return self._s3_client.get_object(
            bucket=self._path_parameters.bucket,
            key=_format_s3_key(
                query_parameters=self._query_parameters,
                directory=self._path_parameters.directory,
                filename=self._objects.filename,
            ),
        )

    def load_ml_model(self, data: bytes, metadata: dict[str, Any], filename: str) -> None:
        self._s3_client.put_object(
            data=data,
            metadata=metadata,
            bucket=self._path_parameters.bucket,
            key=_format_s3_key(
                query_parameters=self._query_parameters, directory=self._path_parameters.directory, filename=filename
            ),
        )

    _repository: None = attr(init=False, default=None)
