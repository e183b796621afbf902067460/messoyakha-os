# pylint: disable=duplicate-code, too-many-lines
from itertools import combinations
from pathlib import Path
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
    assume_fit,
    capture_matchings,
    is_mean_horizontal_in_matchings,
    max_by_matchings,
    mean_by_matchings,
    min_by_matchings,
    quantile_matching_fit,
    set_confidence_degree,
)
from src.settings import settings

filterwarnings("ignore")


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
        .map_elements(function=lambda row: min_by_matchings(row=row, matchings=row["adx_matchings"]))  # noqa: WPS204
        .alias(name="min_adx_matchings")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(function=lambda row: max_by_matchings(row=row, matchings=row["adx_matchings"]))
        .alias(name="max_adx_matchings")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(function=lambda row: mean_by_matchings(row=row, matchings=row["adx_matchings"]))
        .alias(name="mean_adx_matchings")
    )
    data = data.with_columns(
        mean_horizontal("min_adx_matchings", "max_adx_matchings").alias(name="mean_adx_minmax_matchings")
    )

    # TODO: calculate percent of deltas in particular category for each indicator's pair?
    data = data.with_columns(delta_adx_minmax_matchings=col("max_adx_matchings") - col("min_adx_matchings"))
    data = data.with_columns(
        struct(all_columns())
        .map_elements(function=lambda row: set_confidence_degree(delta=row["delta_adx_minmax_matchings"]))
        .alias(name="confidence_degree_adx_matchings")
    )
    data = data.with_columns(
        scaled_delta_adx_minmax_matchings=col("delta_adx_minmax_matchings") / col("length_adx_matchings")
    )

    # TODO: set indicator category? calculate percent of indicators in particular category?
    for adx_column in adx_columns:  # noqa: WPS426
        data = data.with_columns(
            col("adx_matchings").list.contains(item=adx_column).alias(name=f"is_{adx_column}_in_matchings")
        )
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: assume_fit(
                    row=row, assume=adx_column, indicator="adx", matchings=row["adx_matchings"]
                )
            )
            .alias(name=f"assume_{adx_column}_is_target")
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
                function=lambda row: assume_fit(
                    row=row, assume=f"mean_horizontal_{first}_{second}", indicator="adx", matchings=row["adx_matchings"]
                )
            )
            .alias(name=f"assume_adx_mean_horizontal_{first}_{second}_is_target")
        )
    assume_adx_columns: list[str] = [column for column in data.columns if column.startswith("assume_adx")]
    logger.info("Booleans computed.")

    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_matching_fit(
                row=row, target="ticks", indicator="adx", matchings=row["adx_matchings"]
            )
        )
        .alias(name="rank")
    ).drop_nulls(subset=["rank"])
    logger.info(
        f"R2 between target and QMF is {r2_score(y_true=data['ticks'].to_numpy(), y_pred=data['rank'].to_numpy())} "
        f"{data.shape}."
    )

    categorical_features: list[str] = [
        column for column in data.columns if column.startswith("is_adx") or column.startswith("is_mean_horizontal_adx")
    ] + ["length_adx_matchings", "confidence_degree_adx_matchings"]
    feature_columns: list[str] = (
        adx_columns
        + mean_horizontal_adx_columns
        + assume_adx_columns
        + [
            "min_adx_matchings",
            "max_adx_matchings",
            "mean_adx_matchings",
            "mean_adx_minmax_matchings",
            "delta_adx_minmax_matchings",
            "scaled_delta_adx_minmax_matchings",
        ]
        + categorical_features
    )
    data = data.drop_nulls(subset=feature_columns)
    logger.info(f"Shape of data is {data.shape}.")
    logger.info(f"Total number of features is {len(feature_columns)}.")

    data = data.to_pandas()
    for categorical_feature in categorical_features:
        data[categorical_feature] = data[categorical_feature].astype(int)
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
        cat_features=categorical_features,
        weight=train_features["delta_adx_minmax_matchings"],
    )
    test_pool: Pool = Pool(
        data=test_features,
        label=test_target,
        cat_features=categorical_features,
        weight=test_features["delta_adx_minmax_matchings"],
    )

    def objective(trial: Trial) -> float:  # noqa: WPS430
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 1e-3, 5e-1, log=True),  # noqa: WPS432
            "iterations": trial.suggest_int("iterations", 2**8, 2**12),  # noqa: WPS432
            "depth": trial.suggest_int("depth", 2, 12),  # noqa: WPS432
            "max_ctr_complexity": trial.suggest_int("max_ctr_complexity", 2, 12),  # noqa: WPS432
            "rsm": trial.suggest_float("rsm", 5e-2, 9e-1, log=True),  # noqa: WPS432
            "reg_lambda": trial.suggest_float("reg_lambda", 5e-2, 5e-1, log=True),  # noqa: WPS432
            "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 2**4, 2**8),  # noqa: WPS432
        }
        optuna_model: CatBoostRegressor = CatBoostRegressor(
            **params,
            loss_function="MAE",
            random_state=settings.RANDOM_STATE,
            verbose=False,
        )
        optuna_model.fit(X=train_pool, eval_set=test_pool, use_best_model=True, verbose=False)

        test_features["y"] = optuna_model.predict(data=test_pool)
        test_features.loc[test_features["y"] > test_features["max_adx_matchings"], "y"] = test_features[
            "mean_adx_matchings"
        ]
        test_features.loc[test_features["y"] < test_features["min_adx_matchings"], "y"] = test_features[
            "mean_adx_matchings"
        ]

        return float(r2_score(y_true=test_target, y_pred=test_features["y"]))

    study: Study = create_study(direction="maximize", sampler=CmaEsSampler(seed=settings.RANDOM_STATE))
    study.optimize(func=objective, n_trials=100, gc_after_trial=True, show_progress_bar=True)

    filepath: Path = Path(f"{uuid1()}.cbm")
    model: CatBoostRegressor = CatBoostRegressor(
        **study.best_params,
        loss_function="MAE",
        metadata={"columns": str(feature_columns)},
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
