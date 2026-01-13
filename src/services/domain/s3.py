# pylint: disable=too-many-lines, invalid-name
from datetime import datetime
from re import findall
from typing import Any

from attr import attr, attrs
from botocore.errorfactory import ClientError
from pandas import DataFrame

from src.adapters.clients.s3 import S3Client
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.common.duckdb_base import DuckDBBaseRepository
from src.adapters.repositories.indicators import (
    ADXRepository,
    AroonRepository,
    BinariesRepository,
    MARepository,
    MDIRepository,
    PDIRepository,
    RSIRepository,
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
    MDIPathParametersSchema,
    MDIQueryParametersSchema,
    MLModelPathParametersSchema,
    MLModelQueryParametersSchema,
    OHLCPathParametersSchema,
    OHLCQueryParametersSchema,
    PathParametersBaseSchema,
    PDIPathParametersSchema,
    PDIQueryParametersSchema,
    QueryParametersBaseSchema,
    RSIPathParametersSchema,
    RSIQueryParametersSchema,
    SARTrialPathParametersSchema,
    SARTrialQueryParametersSchema,
    StreakPathParametersSchema,
    StreakQueryParametersSchema,
    TradePathParametersSchema,
    TradeQueryParametersSchema,
)


def _findall_prefixes(strings: list[str]) -> list[str]:
    pattern: str = r"\b([a-zA-Z]+_\d+)_(?:open|high|low|close)\b"

    prefixes: list[str] = []
    for string in strings:
        match: list[str] = findall(pattern=pattern, string=string)
        if match and match[0] not in prefixes:
            prefixes.append(match[0])
    return prefixes


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


@attrs(slots=True, auto_attribs=True, kw_only=True)
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
            self._ohlc.drop_duplicates(inplace=True)

    @property
    def ohlc(self) -> DataFrame | None:
        return self._ohlc

    @ohlc.setter
    def ohlc(self, ohlc: DataFrame) -> None:
        self._ohlc = ohlc

    @property
    def latest_timestamp(self) -> DataFrame | None:
        return self._latest_timestamp

    def load_ohlc(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(  # noqa: WPS204
            dataframe=dataframe, key=f"{self._path}/{filename}"
        )

    _ohlc: DataFrame | None = attr(init=False)
    _latest_timestamp: datetime | None = attr(init=False)


@attrs(slots=True, auto_attribs=True, kw_only=True)
class MAService(_S3BaseService):
    _repository: MARepository

    _query_parameters: MAQueryParametersSchema
    _path_parameters: MAPathParametersSchema

    def __attrs_post_init__(self) -> None:
        _S3BaseService.__attrs_post_init__(self=self)
        self._ma: DataFrame | None = self._repository.query_ma(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )
        self._ma_prefixes: list[str] | None = None
        if isinstance(self._ma, DataFrame):
            self._ma_prefixes = _findall_prefixes(strings=self._ma.columns.to_list())
            self._ma.drop_duplicates(inplace=True)

    @property
    def ma(self) -> DataFrame | None:
        return self._ma

    @ma.setter
    def ma(self, ma: DataFrame) -> None:
        self._ma = ma

    @property
    def ma_prefixes(self) -> list[str] | None:
        return self._ma_prefixes

    @staticmethod
    def get_ma_booleans(ma: DataFrame) -> list[str]:
        return [column for column in ma.columns.tolist() if column.startswith("is_")]

    @staticmethod
    def get_ma_streaks(ma: DataFrame) -> list[str]:
        return [column for column in ma.columns.tolist() if column.startswith("streak_")]

    def load_ma(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")

    _ma: DataFrame | None = attr(init=False)
    _ma_prefixes: list[str] | None = attr(init=False)


@attrs(slots=True, auto_attribs=True, kw_only=True)
class ADXService(_S3BaseService):
    _repository: ADXRepository

    _query_parameters: ADXQueryParametersSchema
    _path_parameters: ADXPathParametersSchema

    def __attrs_post_init__(self) -> None:
        _S3BaseService.__attrs_post_init__(self=self)
        self._adx: DataFrame | None = self._repository.query_adx(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )
        if isinstance(self._adx, DataFrame):
            self._adx.drop_duplicates(inplace=True)

    @property
    def adx(self) -> DataFrame | None:
        return self._adx

    @staticmethod
    def get_adx_columns(columns: list[str]) -> list[str]:
        return sorted([column for column in columns if column.startswith("adx")])

    def load_adx(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")

    _adx: DataFrame | None = attr(init=False)


@attrs(slots=True, auto_attribs=True, kw_only=True)
class MDIService(_S3BaseService):
    _repository: MDIRepository

    _query_parameters: MDIQueryParametersSchema
    _path_parameters: MDIPathParametersSchema

    def __attrs_post_init__(self) -> None:
        _S3BaseService.__attrs_post_init__(self=self)
        self._mdi: DataFrame | None = self._repository.query_mdi(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )
        if isinstance(self._mdi, DataFrame):
            self._mdi.drop_duplicates(inplace=True)

    @property
    def mdi(self) -> DataFrame | None:
        return self._mdi

    @staticmethod
    def get_mdi_columns(columns: list[str]) -> list[str]:
        return sorted([column for column in columns if column.startswith("mdi")])

    def load_mdi(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")

    _mdi: DataFrame | None = attr(init=False)


@attrs(slots=True, auto_attribs=True, kw_only=True)
class PDIService(_S3BaseService):
    _repository: PDIRepository

    _query_parameters: PDIQueryParametersSchema
    _path_parameters: PDIPathParametersSchema

    def __attrs_post_init__(self) -> None:
        _S3BaseService.__attrs_post_init__(self=self)
        self._pdi: DataFrame | None = self._repository.query_pdi(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )
        if isinstance(self._pdi, DataFrame):
            self._pdi.drop_duplicates(inplace=True)

    @property
    def pdi(self) -> DataFrame | None:
        return self._pdi

    @staticmethod
    def get_pdi_columns(columns: list[str]) -> list[str]:
        return sorted([column for column in columns if column.startswith("pdi")])

    def load_pdi(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")

    _pdi: DataFrame | None = attr(init=False)


@attrs(slots=True, auto_attribs=True, kw_only=True)
class SARService(_S3BaseService):
    _repository: SARTrialsRepository

    _query_parameters: SARTrialQueryParametersSchema
    _path_parameters: SARTrialPathParametersSchema

    def __attrs_post_init__(self) -> None:
        _S3BaseService.__attrs_post_init__(self=self)
        self._sar_trials: DataFrame | None = self._repository.query_sar_trials(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )
        if isinstance(self._sar_trials, DataFrame):
            self._sar_trials.drop_duplicates(inplace=True)

    @property
    def sar_trials(self) -> DataFrame | None:
        return self._sar_trials

    def load_sar_trials(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")

    _sar_trials: DataFrame | None = attr(init=False)


@attrs(slots=True, auto_attribs=True, kw_only=True)
class EVService(_S3BaseService):
    _repository: TradesRepository

    _query_parameters: TradeQueryParametersSchema
    _path_parameters: TradePathParametersSchema

    def __attrs_post_init__(self) -> None:
        _S3BaseService.__attrs_post_init__(self=self)
        self._ev: DataFrame | None = self._repository.query_trades(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )
        if isinstance(self._ev, DataFrame):
            self._ev.drop_duplicates(inplace=True)

    @property
    def ev(self) -> DataFrame | None:
        return self._ev

    def load_ev(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")

    _ev: DataFrame | None = attr(init=False)


@attrs(slots=True, auto_attribs=True, kw_only=True)
class RSIService(_S3BaseService):
    _repository: RSIRepository

    _query_parameters: RSIQueryParametersSchema
    _path_parameters: RSIPathParametersSchema

    def __attrs_post_init__(self) -> None:
        _S3BaseService.__attrs_post_init__(self=self)
        self._rsi: DataFrame | None = self._repository.query_rsi(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )
        if isinstance(self._rsi, DataFrame):
            self._rsi.drop_duplicates(inplace=True)

    @property
    def rsi(self) -> DataFrame | None:
        return self._rsi

    @staticmethod
    def get_rsi_columns(columns: list[str]) -> list[str]:
        return sorted([column for column in columns if column.startswith("rsi")])

    def load_rsi(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")

    _rsi: DataFrame | None = attr(init=False)


class AroonService(_S3BaseService):
    _repository: AroonRepository

    _query_parameters: AroonQueryParametersSchema
    _path_parameters: AroonPathParametersSchema

    def __attrs_post_init__(self) -> None:
        _S3BaseService.__attrs_post_init__(self=self)
        self._aroon: DataFrame | None = self._repository.query_aroon(
            parameters_schema=self._query_parameters, path=self._formatted_path
        )
        if isinstance(self._aroon, DataFrame):
            self._aroon.drop_duplicates(inplace=True)

    @property
    def aroon(self) -> DataFrame | None:
        return self._aroon

    def load_aroon(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")

    _aroon: DataFrame | None = attr(init=False)


# TODO: ...
class BinaryService(_S3BaseService):
    _repository: BinariesRepository

    _query_parameters: BinaryQueryParametersSchema
    _path_parameters: BinaryPathParametersSchema

    def extract_binary(self) -> DataFrame | None:
        return self._repository.query_binaries(parameters_schema=self._query_parameters, path=self._formatted_path)

    def load_binary(self, dataframe: DataFrame, filename: str) -> None:
        self._repository.insert_dataframe_as_parquet(dataframe=dataframe, key=f"{self._path}/{filename}")


# TODO: ...
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

    def __attrs_post_init__(self) -> None:
        _S3BaseService.__attrs_post_init__(self=self)
        try:
            self._response_schema: GetObjectResponseSchema | None = self._s3_client.get_object(
                bucket=self._path_parameters.bucket,
                key=_format_s3_key(
                    query_parameters=self._query_parameters,
                    directory=self._path_parameters.directory,
                    filename=self._objects.filename,
                ),
            )
        except ClientError:
            self._response_schema = None

    def load_ml_model(self, data: bytes, metadata: dict[str, Any] | None, filename: str) -> None:
        self._s3_client.put_object(
            data=data,
            metadata=metadata,
            bucket=self._path_parameters.bucket,
            key=_format_s3_key(
                query_parameters=self._query_parameters, directory=self._path_parameters.directory, filename=filename
            ),
        )

    _repository: None = attr(init=False, default=None)
    _response_schema: GetObjectResponseSchema | None = attr(init=False)
