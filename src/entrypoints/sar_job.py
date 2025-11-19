# pylint: disable=duplicate-code
from uuid import uuid1

from boto3 import Session
from duckdb import DuckDBPyConnection
from optuna import Study, Trial, create_study
from pandas import DataFrame, Series, concat, to_datetime  # noqa: WPS347

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.indicators import MARepository
from src.adapters.repositories.trials import SARTrialsRepository
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
from src.services.trend import MA, backtest
from src.settings import settings

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
    ohlc_service: OHLCService = OHLCService(
        s3_client=s3_client,
        repository=CandlesticksRepository(connection=duckdb_connection),
        query_parameters=OHLCQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=OHLCPathParametersSchema(bucket=settings.S3_BUCKET, directory="candlesticks"),
    )
    ma_service: MAService = MAService(
        s3_client=s3_client,
        repository=MARepository(connection=duckdb_connection),
        query_parameters=MAQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=MAPathParametersSchema(bucket=settings.S3_BUCKET, directory="moving-averages"),
    )
    sar_service: SARService = SARService(
        s3_client=s3_client,
        repository=SARTrialsRepository(connection=duckdb_connection),
        query_parameters=SARTrialQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=SARTrialPathParametersSchema(bucket=settings.S3_BUCKET, directory="stop-and-reverse-trials"),
    )

    ohlc: DataFrame | None = ohlc_service.extract_ohlc()
    if ohlc is None:
        raise FileNotFoundError("There is no candlesticks data.")
    ohlc.rename(
        mapper={"open": "Open", "high": "High", "low": "Low", "close": "Close", "open_time": "datetime"},
        axis=1,
        inplace=True,
    )
    ohlc.drop(columns=["close_time"], axis=1, inplace=True)
    ohlc.drop_duplicates(inplace=True)

    moving_averages: DataFrame | None = ma_service.extract_ma()
    if moving_averages is None:
        raise FileNotFoundError("There is no moving averages data.")
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
                f"{MA}_open",
                f"{MA}_high",
                f"{MA}_low",
                f"{MA}_close",
            ],
            inplace=True,
        )
        statistics: Series = backtest(
            data=data,
            parameters_schema=SARParametersSchema(
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
    study.optimize(func=objective, n_trials=10_000, n_jobs=12, gc_after_trial=True)  # noqa: WPS432
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

    existing_trials: DataFrame | None = sar_service.extract_sar()
    trials: DataFrame = (
        concat([existing_trials, incoming_trials]) if isinstance(existing_trials, DataFrame) else incoming_trials
    )
    trials.drop_duplicates(inplace=True)
    trials.sort_values(by=["value"], ascending=False, inplace=True)

    sar_service.load_sar(dataframe=trials, filename=f"{uuid1()}.parquet")
    sar_service.delete_object()


# pylint: enable=duplicate-code
