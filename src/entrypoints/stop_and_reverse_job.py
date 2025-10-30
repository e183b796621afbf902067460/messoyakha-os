from typing import Literal
from uuid import uuid1

from backtesting import Backtest
from boto3 import Session
from duckdb import DuckDBPyConnection
from optuna import Study, Trial, create_study
from pandas import DataFrame, Series, concat, to_datetime  # noqa: WPS347
from pydantic import BaseModel, Field
from talib import SAREXT

from src.adapters.clients.s3 import S3Client
from src.adapters.repositories.common.duckdb_base import get_duckdb_connection
from src.adapters.repositories.moving_average import MARepository
from src.adapters.repositories.ohlc import OHLCRepository
from src.adapters.repositories.stop_and_reverse import SARRepository
from src.schemas.backtests import BacktestParametersSchema
from src.schemas.domain.s3 import ListObjectsResponseSchema
from src.schemas.queries import MAQueryParametersSchema, OHLCQueryParametersSchema, SARTrialsQueryParametersSchema
from src.services.common.misc import format_s3_key, format_s3_path
from src.services.trend import TrendStrategy
from src.settings import settings

_KAMA_SIXTY_FOUR: Literal["kama_64"] = "kama_64"


class _SAREXTParametersSchema(BaseModel):

    start_value: float = Field(alias="startvalue")
    offset_on_reverse: float = Field(alias="offsetonreverse")

    acceleration_init_long: float = Field(alias="accelerationinitlong")
    acceleration_init_short: float = Field(alias="accelerationinitshort")

    acceleration_long: float = Field(alias="accelerationlong")
    acceleration_short: float = Field(alias="accelerationshort")

    acceleration_max_long: float = Field(alias="accelerationmaxlong")
    acceleration_max_short: float = Field(alias="accelerationmaxshort")


# pylint: disable=redefined-outer-name
def _main(data: DataFrame, parameters_schema: _SAREXTParametersSchema) -> Series:
    data["sar"] = SAREXT(
        high=data[f"{_KAMA_SIXTY_FOUR}_high"],
        low=data[f"{_KAMA_SIXTY_FOUR}_low"],
        **parameters_schema.model_dump(by_alias=True),
    )
    data["sar"] = abs(data["sar"])

    backtest: Backtest = Backtest(
        data=data,
        strategy=TrendStrategy,
        trade_on_close=True,
        hedging=False,
        finalize_trades=False,
        exclusive_orders=True,
        **BacktestParametersSchema().model_dump(),
    )
    statistics: Series = backtest.run(
        sar_on_bull_market_prefix="sar",
        ma_on_bull_market_prefix=_KAMA_SIXTY_FOUR,
        sar_on_bear_market_prefix="sar",
        ma_on_bear_market_prefix=_KAMA_SIXTY_FOUR,
    )
    return statistics


# pylint: enable=redefined-outer-name


if __name__ == "__main__":
    s3_client: S3Client = S3Client(
        session=Session(
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION_NAME,
        )
    )
    duckdb_connection: DuckDBPyConnection = get_duckdb_connection(
        s3_access_key_id=settings.S3_ACCESS_KEY_ID,
        s3_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        s3_endpoint_url=settings.S3_ENDPOINT_URL.host,
        s3_region_name=settings.S3_REGION_NAME,
    )
    ohlc_repository: OHLCRepository = OHLCRepository(connection=duckdb_connection)
    ma_repository: MARepository = MARepository(connection=duckdb_connection)
    sar_repository: SARRepository = SARRepository(connection=duckdb_connection)

    s3_ohlc_path: str = format_s3_path(exchange=settings.EXCHANGE, section=settings.SECTION, directory="candlesticks")
    s3_ma_path: str = format_s3_path(exchange=settings.EXCHANGE, section=settings.SECTION, directory="moving-averages")
    s3_sar_path: str = format_s3_path(
        exchange=settings.EXCHANGE, section=settings.SECTION, directory="stops-and-reverses"
    )
    s3_trials_path: str = format_s3_path(
        exchange=settings.EXCHANGE, section=settings.SECTION, directory="stop-and-reverse-trials"
    )
    list_ohlc_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="candlesticks"),
    )
    list_ma_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="moving-averages"),
    )
    list_sar_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="stops-and-reverses"),
    )
    list_trial_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="stop-and-reverse-trials"),
    )

    ohlc: DataFrame | None = ohlc_repository.query_candlesticks(
        parameters_schema=OHLCQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path=(
            f"{s3_ohlc_path}/{list_ohlc_objects_response.filename}"
            if list_ohlc_objects_response.filename
            else f"{s3_ohlc_path}/"
        ),
    )
    if ohlc is None:
        raise FileNotFoundError(f"There is no moving averages data in {s3_ohlc_path}.")
    ohlc.rename(
        mapper={"open": "Open", "high": "High", "low": "Low", "close": "Close", "open_time": "datetime"},
        axis=1,
        inplace=True,
    )
    ohlc.drop(columns=["close_time"], axis=1, inplace=True)
    ohlc.drop_duplicates(inplace=True)

    moving_averages: DataFrame | None = ma_repository.query_moving_averages(
        parameters_schema=MAQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path=(
            f"{s3_ma_path}/{list_ma_objects_response.filename}"
            if list_ma_objects_response.filename
            else f"{s3_ma_path}/"
        ),
    )
    if moving_averages is None:
        raise FileNotFoundError(f"There is no moving averages data in {s3_ma_path}.")
    moving_averages.drop_duplicates(inplace=True)

    ohlc = ohlc.merge(right=moving_averages, how="left", on=["exchange", "section", "ticker", "interval", "datetime"])
    ohlc["datetime"] = to_datetime(ohlc["datetime"])
    ohlc["year"] = ohlc["datetime"].dt.year
    ohlc.set_index(keys="datetime", inplace=True)

    def objective(trial: Trial) -> float:
        data: DataFrame = ohlc.copy(deep=True)  # type: ignore[union-attr]
        data.query(f"year < {settings.TRIGGER_DATE.year - 1}", inplace=True)
        data.dropna(
            subset=[
                f"{_KAMA_SIXTY_FOUR}_open",
                f"{_KAMA_SIXTY_FOUR}_high",
                f"{_KAMA_SIXTY_FOUR}_low",
                f"{_KAMA_SIXTY_FOUR}_close",
            ],
            inplace=True,
        )
        statistics: Series = _main(
            data=data,
            parameters_schema=_SAREXTParametersSchema(
                startvalue=trial.suggest_float(name="startvalue", low=1e-4, high=1e-2, log=True),  # noqa: WPS432
                offsetonreverse=trial.suggest_float(
                    name="offsetonreverse", low=1e-4, high=1e-2, log=True  # noqa: WPS432
                ),
                accelerationinitlong=trial.suggest_float(
                    name="accelerationinitlong", low=2e-2, high=7e-2, log=True  # noqa: WPS432
                ),
                accelerationinitshort=trial.suggest_float(
                    name="accelerationinitshort", low=2e-2, high=7e-2, log=True  # noqa: WPS432
                ),
                accelerationlong=trial.suggest_float(
                    name="accelerationlong", low=2e-3, high=2e-2, log=True  # noqa: WPS432
                ),
                accelerationshort=trial.suggest_float(
                    name="accelerationshort", low=2e-3, high=2e-2, log=True  # noqa: WPS432
                ),
                accelerationmaxlong=trial.suggest_float(
                    name="accelerationmaxlong", low=2e-2, high=1e-1, log=True  # noqa: WPS432
                ),
                accelerationmaxshort=trial.suggest_float(
                    name="accelerationmaxshort", low=2e-2, high=1e-1, log=True  # noqa: WPS432
                ),
            ),
        )
        cagr: float = statistics.iloc[11] / 10**2  # noqa: WPS432
        drawdown: float = statistics.iloc[17] / 10**2  # noqa: WPS432
        return cagr / abs(drawdown)

    study: Study = create_study(direction="maximize")
    study.optimize(func=objective, n_trials=2000, n_jobs=12, gc_after_trial=True)  # noqa: WPS432
    incoming_trials: DataFrame = study.trials_dataframe()
    incoming_trials = incoming_trials[
        [
            "value",
            "params_startvalue",
            "params_offsetonreverse",
            "params_accelerationinitlong",
            "params_accelerationinitshort",
            "params_accelerationlong",
            "params_accelerationshort",
            "params_accelerationmaxlong",
            "params_accelerationmaxshort",
            "state",
        ]
    ]
    incoming_trials.rename(
        mapper={
            "params_startvalue": "startvalue",
            "params_offsetonreverse": "offsetonreverse",
            "params_accelerationinitlong": "accelerationinitlong",
            "params_accelerationinitshort": "accelerationinitshort",
            "params_accelerationlong": "accelerationlong",
            "params_accelerationshort": "accelerationshort",
            "params_accelerationmaxlong": "accelerationmaxlong",
            "params_accelerationmaxshort": "accelerationmaxshort",
        },
        axis=1,
        inplace=True,
    )
    incoming_trials["exchange"] = settings.EXCHANGE
    incoming_trials["section"] = settings.SECTION
    incoming_trials["ticker"] = settings.TICKER
    incoming_trials["interval"] = settings.INTERVAL

    existing_trials: DataFrame | None = sar_repository.query_stop_and_reverse_trials(
        parameters_schema=SARTrialsQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path=(
            f"{s3_trials_path}/{list_trial_objects_response.filename}"
            if list_trial_objects_response.filename
            else f"{s3_trials_path}/"
        ),
    )
    trials: DataFrame = (
        concat([existing_trials, incoming_trials]) if isinstance(existing_trials, DataFrame) else incoming_trials
    )
    trials.drop_duplicates(inplace=True)
    trials.sort_values(by=["value"], ascending=False, inplace=True)

    sar_repository.insert_dataframe_as_parquet(dataframe=trials, key=f"{s3_trials_path}/{uuid1()}.parquet")
    if list_trial_objects_response.filename:
        s3_client.delete_object(
            bucket=settings.S3_BUCKET,
            key=format_s3_key(
                exchange=settings.EXCHANGE,
                section=settings.SECTION,
                directory="stop-and-reverse-trials",
                filename=list_trial_objects_response.filename,
            ),
        )

    position: int = int(0.05 * len(trials)) - 1  # noqa: WPS432
    parameters_schema: _SAREXTParametersSchema = _SAREXTParametersSchema(**trials.iloc[position].to_dict())

    ohlc["sar"] = SAREXT(
        high=ohlc[f"{_KAMA_SIXTY_FOUR}_high"],
        low=ohlc[f"{_KAMA_SIXTY_FOUR}_low"],
        **parameters_schema.model_dump(by_alias=True),
    )
    ohlc["sar"] = abs(ohlc["sar"])
    ohlc.reset_index(inplace=True)

    stops_and_reverses: DataFrame = ohlc[["exchange", "section", "ticker", "interval", "sar", "datetime"]].copy(
        deep=True
    )
    sar_repository.insert_dataframe_as_parquet(dataframe=stops_and_reverses, key=f"{s3_sar_path}/{uuid1()}.parquet")
    if list_sar_objects_response.filename:
        s3_client.delete_object(
            bucket=settings.S3_BUCKET,
            key=format_s3_key(
                exchange=settings.EXCHANGE,
                section=settings.SECTION,
                directory="stops-and-reverses",
                filename=list_sar_objects_response.filename,
            ),
        )
