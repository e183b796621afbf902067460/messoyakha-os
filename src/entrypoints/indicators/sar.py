# pylint: disable=duplicate-code
from uuid import uuid1

from backtesting import Backtest
from boto3 import Session
from duckdb import DuckDBPyConnection
from loguru import logger
from optuna import Study, Trial, create_study
from optuna.samplers import CmaEsSampler
from pandas import DataFrame, Series, to_datetime  # noqa: WPS347
from pydantic import BaseModel
from sklearn.model_selection import train_test_split
from talib import SAREXT

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.indicators import MARepository
from src.adapters.repositories.trials import SARTrialsRepository
from src.schemas.backtests import BacktestParametersSchema
from src.schemas.filters import (
    MAPathParametersSchema,
    MAQueryParametersSchema,
    OHLCPathParametersSchema,
    OHLCQueryParametersSchema,
    SARTrialPathParametersSchema,
    SARTrialQueryParametersSchema,
)
from src.schemas.trials import SARParametersSchema
from src.services.domain.s3 import MAService, OHLCService, SARService
from src.services.trends import TrendStrategy
from src.settings import settings


class _MainSchema(BaseModel):
    ohlc_service: OHLCService
    ma_service: MAService
    sar_service: SARService

    class Config:
        arbitrary_types_allowed = True


# pylint: disable=too-many-statements
def _main(main_schema: _MainSchema) -> None:  # noqa: WPS213
    if main_schema.ohlc_service.ohlc is None:
        raise FileNotFoundError("There is no candlesticks data.")
    main_schema.ohlc_service.ohlc.rename(
        mapper={"open": "Open", "high": "High", "low": "Low", "close": "Close", "open_time": "datetime"},
        axis=1,
        inplace=True,
    )
    main_schema.ohlc_service.ohlc.drop(columns=["close_time"], axis=1, inplace=True)

    if main_schema.ma_service.ma is None:
        raise FileNotFoundError("There is no moving averages data.")

    data: DataFrame = main_schema.ohlc_service.ohlc.merge(
        right=main_schema.ma_service.ma, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )
    data["datetime"] = to_datetime(data["datetime"])  # noqa: WPS204
    data["year"] = data["datetime"].dt.year

    data, test, _, _ = train_test_split(
        data, data[["ticker"]], train_size=settings.TRAIN_SIZE, random_state=settings.RANDOM_STATE, shuffle=False
    )
    logger.info(f"The train dataset startswith {data['datetime'].min()} and endswith {data['datetime'].max()}.")
    logger.info(f"The test dataset startswith {test['datetime'].min()} and endswith {test['datetime'].max()}.")

    data.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)
    data.sort_values(by=["datetime"], ascending=True, inplace=True)
    data.set_index(keys="datetime", inplace=True)

    def objective(trial: Trial, train: DataFrame = data.copy(deep=True)) -> float:  # noqa: WPS430
        parameters: SARParametersSchema = SARParametersSchema(
            startvalue=trial.suggest_float(name="startvalue", low=1e-4, high=1e-2, log=True),  # noqa: WPS432
            offsetonreverse=trial.suggest_float(name="offsetonreverse", low=1e-4, high=1e-2, log=True),  # noqa: WPS432
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
        )
        train["sar"] = SAREXT(high=train["High"], low=train["Low"], **parameters.model_dump(by_alias=True))
        train["sar"] = abs(train["sar"])
        test: Backtest = Backtest(
            data=train,
            strategy=TrendStrategy,
            trade_on_close=True,
            hedging=False,
            finalize_trades=False,
            exclusive_orders=True,
            **BacktestParametersSchema().model_dump(),
        )
        statistics: Series = test.run()

        cagr: float = statistics.iloc[11] / 10**2  # noqa: WPS432
        drawdown: float = statistics.iloc[17] / 10**2  # noqa: WPS432
        return cagr / abs(drawdown)

    study: Study = create_study(direction="maximize", sampler=CmaEsSampler(seed=settings.RANDOM_STATE))
    study.optimize(func=objective, n_trials=1000, n_jobs=12, gc_after_trial=True)  # noqa: WPS432
    sar_trials: DataFrame = study.trials_dataframe()
    sar_trials = sar_trials[
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
    sar_trials.rename(
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
    sar_trials["exchange"] = settings.EXCHANGE
    sar_trials["section"] = settings.SECTION
    sar_trials["ticker"] = settings.TICKER
    sar_trials["interval"] = settings.INTERVAL
    sar_trials.drop_duplicates(inplace=True)
    sar_trials.sort_values(by=["value"], ascending=False, inplace=True)

    main_schema.sar_service.load_sar_trials(dataframe=sar_trials, filename=f"{uuid1()}.parquet")
    main_schema.sar_service.delete_object()


# pylint: enable=too-many-statements


# pylint: disable=duplicate-code
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
    _main(
        main_schema=_MainSchema(
            ohlc_service=OHLCService(
                s3_client=s3_client,
                repository=CandlesticksRepository(connection=duckdb_connection),
                query_parameters=OHLCQueryParametersSchema(
                    ticker=settings.TICKER,
                    exchange=settings.EXCHANGE,
                    section=settings.SECTION,
                    interval=settings.INTERVAL,
                ),
                path_parameters=OHLCPathParametersSchema(bucket=settings.S3_BUCKET),
            ),
            ma_service=MAService(
                s3_client=s3_client,
                repository=MARepository(connection=duckdb_connection),
                query_parameters=MAQueryParametersSchema(
                    ticker=settings.TICKER,
                    exchange=settings.EXCHANGE,
                    section=settings.SECTION,
                    interval=settings.INTERVAL,
                ),
                path_parameters=MAPathParametersSchema(bucket=settings.S3_BUCKET),
            ),
            sar_service=SARService(
                s3_client=s3_client,
                repository=SARTrialsRepository(connection=duckdb_connection),
                query_parameters=SARTrialQueryParametersSchema(
                    ticker=settings.TICKER,
                    exchange=settings.EXCHANGE,
                    section=settings.SECTION,
                    interval=settings.INTERVAL,
                ),
                path_parameters=SARTrialPathParametersSchema(bucket=settings.S3_BUCKET),
            ),
        )
    )


# pylint: enable=duplicate-code
