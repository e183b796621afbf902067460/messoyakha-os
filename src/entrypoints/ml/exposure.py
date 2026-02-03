# pylint: disable=duplicate-code, too-many-lines
from itertools import combinations
from pathlib import Path
from typing import Final
from uuid import uuid1
from warnings import filterwarnings

from boto3 import Session
from catboost import CatBoostRegressor, Pool
from duckdb import DuckDBPyConnection
from loguru import logger
from numpy import log1p, vstack
from optuna import Study, Trial, create_study
from optuna.samplers import CmaEsSampler
from pandas import DataFrame, to_datetime  # noqa: WPS347
from polars import DataFrame as PolarsDF
from polars import all as all_columns
from polars import col, mean_horizontal, struct
from pydantic import BaseModel, Field
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.indicators import ADXRepository, MARepository
from src.adapters.repositories.trades import TradesRepository
from src.schemas.filters import (
    ADXPathParametersSchema,
    ADXQueryParametersSchema,
    MAPathParametersSchema,
    MAQueryParametersSchema,
    MLModelPathParametersSchema,
    MLModelQueryParametersSchema,
    TradePathParametersSchema,
    TradeQueryParametersSchema,
)
from src.services.domain.s3 import ADXService, EVService, MAService, MLModelService
from src.services.statistics import (
    af,
    capture_matchings,
    is_mean_horizontal_in_matchings,
    median_by_matchings,
    median_high_spread_by_matchings,
    median_low_spread_by_matchings,
    qmf,
    quantile_by_matchings,
)
from src.settings import settings

filterwarnings("ignore")


_LOWEST_QUANTILE: Final[float] = 0.2
_LOWEST_HALF_QUANTILE: Final[float] = 0.35
_HIGHEST_HALF_QUANTILE: Final[float] = 0.65
_HIGHEST_QUANTILE: Final[float] = 0.8


class _MainSchema(BaseModel):
    ma_service: MAService
    adx_service: ADXService
    ev_service: EVService

    ml_model_service: MLModelService

    scaler: MinMaxScaler = Field(default_factory=MinMaxScaler)

    class Config:
        arbitrary_types_allowed = True


# pylint: disable=too-many-locals, too-many-statements, too-complex, cell-var-from-loop, protected-access
def _main(main_schema: _MainSchema) -> None:  # noqa: WPS213
    if main_schema.ma_service.ma is None:
        raise FileNotFoundError("There is no moving averages data.")
    ma_booleans: list[str] = main_schema.ma_service.get_ma_booleans(ma=main_schema.ma_service.ma)
    ma_streaks: list[str] = main_schema.ma_service.get_ma_streaks(ma=main_schema.ma_service.ma)
    main_schema.ma_service.ma = main_schema.ma_service.ma[
        ["exchange", "section", "ticker", "interval", "datetime"] + ma_booleans + ma_streaks
    ]

    if main_schema.adx_service.adx is None:
        raise FileNotFoundError("There is no ADX data.")
    adx_columns: list[str] = main_schema.adx_service.get_adx_columns(
        columns=main_schema.adx_service.adx.columns.tolist()
    )

    if main_schema.ev_service.ev is None:
        raise FileNotFoundError("There is no trades data.")
    logger.info(f"Shape of EV is {main_schema.ev_service.ev.shape}.")

    data: DataFrame | PolarsDF = main_schema.ev_service.ev.merge(
        right=main_schema.ma_service.ma, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )
    data = data.merge(
        right=main_schema.adx_service.adx, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )
    data["datetime"] = to_datetime(data["datetime"])
    data["year"] = data["datetime"].dt.year
    data.query("ticks > 1", inplace=True)
    data.dropna(inplace=True)

    data["ticks"] = log1p(data["ticks"])  # noqa: WPS204
    _, _, train_rank, _ = train_test_split(
        data, data[["ticks"]], train_size=settings.TRAIN_SIZE, random_state=settings.RANDOM_STATE, shuffle=False
    )
    main_schema.scaler.fit(X=vstack(tup=train_rank["ticks"]))
    data["ticks"] = main_schema.scaler.transform(X=vstack(tup=data["ticks"])).flatten()
    logger.info("Scaler is fitted.")

    # ---

    data = PolarsDF(data=data)

    # TODO: r=3, r=4 etc. and add them to QMF-function
    for first, second in combinations(iterable=adx_columns, r=2):
        data = data.with_columns(mean_horizontal(first, second).alias(name=f"mean_horizontal_{first}_{second}"))
    mean_horizontal_adx_columns: list[str] = [
        column for column in data.columns if column.startswith("mean_horizontal_adx")
    ]

    data = data.with_columns(
        struct(all_columns())  # noqa: WPS204
        .map_elements(
            function=lambda row: capture_matchings(
                row=row,
                ma_prefixes=main_schema.ma_service.ma_prefixes,
                potentials=adx_columns,
            )
        )
        .alias(name="adx_matchings")
    )
    data = data.with_columns(length_adx_matchings=col("adx_matchings").list.len())
    data = data.filter((col("length_adx_matchings") > 1))

    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=row["adx_matchings"], q=_LOWEST_QUANTILE  # noqa: WPS204
            )
        )
        .alias(name="quantile_adx_matchings_low")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(row=row, matchings=row["adx_matchings"], q=_LOWEST_HALF_QUANTILE)
        )
        .alias(name="quantile_adx_matchings_half_low")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(function=lambda row: median_by_matchings(row=row, matchings=row["adx_matchings"]))
        .alias(name="median_adx_matchings")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=row["adx_matchings"], q=_HIGHEST_HALF_QUANTILE
            )
        )
        .alias(name="quantile_adx_matchings_half_high")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(row=row, matchings=row["adx_matchings"], q=_HIGHEST_QUANTILE)
        )
        .alias(name="quantile_adx_matchings_high")
    )
    data = data.with_columns(
        delta_adx_quantile_matchings=col("quantile_adx_matchings_high") - col("quantile_adx_matchings_low")
    )
    data = data.with_columns(
        scaled_delta_adx_quantile_matchings=col("delta_adx_quantile_matchings") / col("length_adx_matchings")
    )

    for adx_column in adx_columns + [  # noqa: WPS426
        "quantile_adx_matchings_low",
        "quantile_adx_matchings_half_low",
        "median_adx_matchings",
        "quantile_adx_matchings_half_high",
        "quantile_adx_matchings_high",
    ]:
        data = data.with_columns(
            col("adx_matchings").list.contains(item=adx_column).alias(name=f"is_{adx_column}_in_matchings")
        )
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: af(row=row, assume=adx_column, indicator="adx", matchings=row["adx_matchings"])
            )
            .alias(name=f"assume_{adx_column}_is_target")
        )
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: af(
                    row=row, assume=adx_column, indicator="adx", matchings=row["adx_matchings"], is_reversed=True
                )
            )
            .alias(name=f"reversed_assume_{adx_column}_is_target")
        )
    for first, second in combinations(iterable=adx_columns, r=2):  # noqa: WPS426 WPS440
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: is_mean_horizontal_in_matchings(
                    first=first, second=second, matchings=row["adx_matchings"]
                )
            )
            .alias(name=f"is_mean_horizontal_{first}_{second}_in_matchings")
        )
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: af(
                    row=row, assume=f"mean_horizontal_{first}_{second}", indicator="adx", matchings=row["adx_matchings"]
                )
            )
            .alias(name=f"assume_mean_horizontal_{first}_{second}_is_target")
        )
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: af(
                    row=row,
                    assume=f"mean_horizontal_{first}_{second}",
                    indicator="adx",
                    matchings=row["adx_matchings"],
                    is_reversed=True,
                )
            )
            .alias(name=f"reversed_assume_mean_horizontal_{first}_{second}_is_target")
        )
    assume_adx_columns: list[str] = [column for column in data.columns if column.startswith("assume")]
    reversed_assume_adx_columns: list[str] = [column for column in data.columns if column.startswith("reversed_assume")]
    logger.info("Booleans and assumes computed.")

    # TODO: [assume_adx_columns, reversed_assume_adx_columns]
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=assume_adx_columns, q=_LOWEST_QUANTILE, is_assume=True
            )
        )
        .alias(name="quantile_assume_adx_matchings_low")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=assume_adx_columns, q=_LOWEST_HALF_QUANTILE, is_assume=True
            )
        )
        .alias(name="quantile_assume_adx_matchings_half_low")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(function=lambda row: median_by_matchings(row=row, matchings=assume_adx_columns, is_assume=True))
        .alias(name="median_assume_adx_matchings")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=assume_adx_columns, q=_HIGHEST_HALF_QUANTILE, is_assume=True
            )
        )
        .alias(name="quantile_assume_adx_matchings_half_high")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=assume_adx_columns, q=_HIGHEST_QUANTILE, is_assume=True
            )
        )
        .alias(name="quantile_assume_adx_matchings_high")
    )
    data = data.with_columns(
        delta_quantile_adx_quantile_matchings=(
            col("quantile_assume_adx_matchings_high") - col("quantile_assume_adx_matchings_low")
        )
    )
    data = data.with_columns(
        scaled_delta_quantile_adx_quantile_matchings=(
            col("delta_quantile_adx_quantile_matchings") / col("length_adx_matchings")
        )
    )
    quantile_assume_adx_columns: list[str] = [
        column
        for column in data.columns
        if column.startswith("quantile_assume_adx") or column.startswith("median_assume_adx")
    ]
    logger.info("Quantile assumes computed.")

    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: median_low_spread_by_matchings(row=row, matchings=assume_adx_columns, indicator="adx")
        )
        .alias(name="spread_low_adx_matchings")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: median_high_spread_by_matchings(row=row, matchings=assume_adx_columns, indicator="adx")
        )
        .alias(name="spread_high_adx_matchings")
    )

    data = (
        data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: qmf(row=row, target="ticks", indicator="adx", matchings=row["adx_matchings"])
            )
            .alias(name="rank")
        )
        .drop_nulls(subset=["rank"])
        .drop_nans(subset=["rank"])
    )
    logger.info(
        f"R2 between target and QMF is {r2_score(y_true=data['ticks'].to_numpy(), y_pred=data['rank'].to_numpy())} "
        f"{data.shape}."
    )

    categorical_columns: list[str] = [
        column for column in data.columns if column.startswith("is_adx") or column.startswith("is_mean_horizontal_adx")
    ] + ["is_long", "length_adx_matchings"]
    feature_columns: list[str] = (
        adx_columns
        + mean_horizontal_adx_columns
        + [
            "quantile_adx_matchings_low",
            "quantile_adx_matchings_half_low",
            "median_adx_matchings",
            "quantile_adx_matchings_half_high",
            "quantile_adx_matchings_high",
            "delta_adx_quantile_matchings",
            "scaled_delta_adx_quantile_matchings",
            "delta_quantile_adx_quantile_matchings",
            "scaled_delta_quantile_adx_quantile_matchings",
            "spread_low_adx_matchings",
            "spread_high_adx_matchings",
        ]
        + assume_adx_columns
        + quantile_assume_adx_columns
        + reversed_assume_adx_columns
        + categorical_columns
    )
    data = data.drop_nulls(subset=feature_columns)
    logger.info(f"Shape of data is {data.shape}.")
    logger.info(f"Total number of features is {len(feature_columns)}.")

    data = data.to_pandas()
    for categorical_column in categorical_columns:
        data[categorical_column] = data[categorical_column].astype(int)
    train_features, test_features, train_target, test_target = train_test_split(
        data[feature_columns],
        data[["rank"]],
        train_size=settings.TRAIN_SIZE,
        random_state=settings.RANDOM_STATE,
        shuffle=False,
    )
    train_pool: Pool = Pool(
        data=train_features,
        label=train_target,
        cat_features=categorical_columns,
        weight=train_features["delta_quantile_adx_quantile_matchings"],
    )
    test_pool: Pool = Pool(
        data=test_features,
        label=test_target,
        cat_features=categorical_columns,
        weight=test_features["delta_quantile_adx_quantile_matchings"],
    )

    # TODO: sum_models with different loss functions
    def objective(trial: Trial) -> float:  # noqa: WPS430
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 1e-3, 5e-1, log=True),  # noqa: WPS432
            "iterations": trial.suggest_int("iterations", 2**4, 2**12),  # noqa: WPS432
            "depth": trial.suggest_int("depth", 2, 12),  # noqa: WPS432
            "max_ctr_complexity": trial.suggest_int("max_ctr_complexity", 2, 12),  # noqa: WPS432
            "rsm": trial.suggest_float("rsm", 1e-1, 9e-1, log=True),  # noqa: WPS432
            "reg_lambda": trial.suggest_float("reg_lambda", 5e-2, 5e-1, log=True),  # noqa: WPS432
            "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 2**4, 2**8),  # noqa: WPS432
        }
        optuna_model: CatBoostRegressor = CatBoostRegressor(
            **params,
            loss_function="RMSE",
            custom_metric=["R2"],
            random_state=settings.RANDOM_STATE,
            verbose=False,
        )
        optuna_model.fit(X=train_pool, eval_set=test_pool, use_best_model=True, verbose=False)
        return float(optuna_model.get_best_score()["validation"]["R2:use_weights=true"])

    study: Study = create_study(direction="maximize", sampler=CmaEsSampler(seed=settings.RANDOM_STATE))
    study.optimize(func=objective, n_trials=100, gc_after_trial=True, show_progress_bar=True)

    filepath: Path = Path(f"{uuid1()}.cbm")
    model: CatBoostRegressor = CatBoostRegressor(
        **study.best_params,
        loss_function="RMSE",
        metadata={
            "ma_prefixes": str(main_schema.ma_service.ma_prefixes),
            "adx_columns": str(adx_columns),
            "categorical_columns": str(categorical_columns),
            "feature_columns": str(feature_columns)
        },
        random_state=settings.RANDOM_STATE,
        verbose=False,
    )
    model.fit(X=train_pool, eval_set=test_pool, use_best_model=True, verbose=False)
    main_schema.ml_model_service.load_ml_model(
        data=model._serialize_model(), metadata=None, filename=filepath.as_posix()
    )


# pylint: enable=too-many-locals, too-many-statements, too-complex, cell-var-from-loop, protected-access


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
            adx_service=ADXService(
                s3_client=s3_client,
                repository=ADXRepository(connection=duckdb_connection),
                query_parameters=ADXQueryParametersSchema(
                    ticker=settings.TICKER,
                    exchange=settings.EXCHANGE,
                    section=settings.SECTION,
                    interval=settings.INTERVAL,
                ),
                path_parameters=ADXPathParametersSchema(bucket=settings.S3_BUCKET),
            ),
            ev_service=EVService(
                s3_client=s3_client,
                repository=TradesRepository(connection=duckdb_connection),
                query_parameters=TradeQueryParametersSchema(
                    ticker=settings.TICKER,
                    exchange=settings.EXCHANGE,
                    section=settings.SECTION,
                    interval=settings.INTERVAL,
                ),
                path_parameters=TradePathParametersSchema(bucket=settings.S3_BUCKET),
            ),
            ml_model_service=MLModelService(
                s3_client=s3_client,
                query_parameters=MLModelQueryParametersSchema(
                    ticker=settings.TICKER,
                    exchange=settings.EXCHANGE,
                    section=settings.SECTION,
                    interval=settings.INTERVAL,
                ),
                path_parameters=MLModelPathParametersSchema(bucket=settings.S3_BUCKET, directory="exposure"),
            ),
        )
    )


# pylint: enable=duplicate-code,too-complex,cell-var-from-loop
