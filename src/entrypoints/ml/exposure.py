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
from onnx import ModelProto, StringStringEntryProto, load_model
from optuna import Study, Trial, create_study
from optuna.samplers import CmaEsSampler
from pandas import DataFrame, to_datetime  # noqa: WPS347
from polars import DataFrame as PolarsDF
from polars import all as all_columns
from polars import col, mean_horizontal, struct
from pydantic import BaseModel, Field
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

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
from src.services.statistic import (
    determine_matching_columns,
    is_mean_horizontal_in_matching_columns,
    matching_max,
    matching_mean,
    matching_min,
    quantile_matching_fit,
    set_market_regime,
)
from src.settings import settings

filterwarnings("ignore")


class _MainSchema(BaseModel):
    ma_service: MAService
    adx_service: ADXService
    ev_service: EVService

    ml_model_service: MLModelService

    scaler: MinMaxScaler = Field(default_factory=MinMaxScaler)
    encoder: LabelEncoder = Field(default_factory=LabelEncoder)

    class Config:
        arbitrary_types_allowed = True


# pylint: disable=too-many-locals, too-many-statements, too-complex, cell-var-from-loop
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
    for first, second in combinations(iterable=adx_columns, r=2):
        data = data.with_columns(mean_horizontal(first, second).alias(name=f"mean_horizontal_{first}_{second}"))
    mean_adx_columns: list[str] = [column for column in data.columns if column.startswith("mean_horizontal")]

    data = data.with_columns(
        struct(all_columns())  # noqa: WPS204
        .map_elements(
            function=lambda row: determine_matching_columns(
                row=row,
                ma_prefixes=main_schema.ma_service.ma_prefixes,  # type: ignore[arg-type]
                potential_columns=adx_columns,
            )
        )
        .alias(name="matching_columns")
    )
    data = data.with_columns(matching_columns_length=col("matching_columns").list.len())
    data = data.filter((col("matching_columns_length") > 1))

    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: matching_min(row=row, matching_columns=row["matching_columns"])  # noqa: WPS204
        )
        .alias(name="matching_min")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(function=lambda row: matching_max(row=row, matching_columns=row["matching_columns"]))
        .alias(name="matching_max")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(function=lambda row: matching_mean(row=row, matching_columns=row["matching_columns"]))
        .alias(name="matching_mean")
    )
    data = data.with_columns(mean_horizontal("matching_min", "matching_max").alias(name="matching_minmax_mean"))
    data = data.with_columns(matching_minmax_delta=col("matching_max") - col("matching_min"))
    data = data.with_columns(
        struct(all_columns())
        .map_elements(function=lambda row: set_market_regime(delta=row["matching_minmax_delta"]))
        .alias(name="market_regime")
    )

    for adx_column in adx_columns:
        data = data.with_columns(
            col("matching_columns").list.contains(item=adx_column).alias(name=f"is_{adx_column}_in_matching_columns")
        )
    for first, second in combinations(iterable=adx_columns, r=2):  # noqa: WPS426 WPS440
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: is_mean_horizontal_in_matching_columns(
                    first=first, second=second, matching_columns=row["matching_columns"]
                )
            )
            .alias(name=f"is_mean_horizontal_{first}_{second}_in_matching_columns")
        )
    logger.info("Booleans computed.")

    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_matching_fit(
                row=row, target_column="ticks", matching_columns=row["matching_columns"]
            )
        )
        .alias(name="rank")
    ).drop_nulls(subset=["rank"])
    logger.info(
        f"R2 between target and QMF is {r2_score(y_true=data['ticks'].to_numpy(), y_pred=data['rank'].to_numpy())} "
        f"{data.shape}."
    )

    categorical_features: list[str] = [column for column in data.columns if column.startswith("is")] + [
        "matching_columns_length",
        "market_regime",
    ]
    feature_columns: list[str] = (
        adx_columns
        + mean_adx_columns
        + ["matching_min", "matching_max", "matching_mean", "matching_minmax_mean", "matching_minmax_delta"]
        + ma_streaks
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
    train_pool: Pool = Pool(data=train_features, label=train_target)
    test_pool: Pool = Pool(data=test_features, label=test_target)

    def objective(trial: Trial) -> float:  # noqa: WPS430
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 1e-3, 5e-1, log=True),  # noqa: WPS432
            "iterations": trial.suggest_int("iterations", 2**8, 2**12),  # noqa: WPS432
            "depth": trial.suggest_int("depth", 2, 12),  # noqa: WPS432
            "max_ctr_complexity": trial.suggest_int("max_ctr_complexity", 2, 12),  # noqa: WPS432
            "reg_lambda": trial.suggest_float("reg_lambda", 5e-2, 5e-1, log=True),  # noqa: WPS432
            "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 2**2, 2**6),  # noqa: WPS432
        }
        optuna_model: CatBoostRegressor = CatBoostRegressor(
            **params,
            loss_function="MAE",
            eval_metric="MAE",
            custom_metric=["MAE"],
            random_state=settings.RANDOM_STATE,
            verbose=False,
        )
        optuna_model.fit(X=train_pool, eval_set=test_pool, use_best_model=True, verbose=False)
        return float(optuna_model.score(X=test_pool))

    study: Study = create_study(direction="maximize", sampler=CmaEsSampler(seed=settings.RANDOM_STATE))
    study.optimize(func=objective, n_trials=10, gc_after_trial=True, show_progress_bar=True)

    model: CatBoostRegressor = CatBoostRegressor(
        **study.best_params,
        loss_function="MAE",
        eval_metric="MAE",
        custom_metric=["MAE"],
        random_state=settings.RANDOM_STATE,
        verbose=False,
    )
    model.fit(X=train_pool, eval_set=test_pool, use_best_model=True, verbose=False)

    filepath: Path = Path(f"{uuid1()}.onnx")
    model.save_model(fname=filepath.as_posix(), format="onnx", pool=train_pool)
    proto: ModelProto = load_model(f=filepath.as_posix())
    filepath.unlink()

    proto.metadata_props.append(StringStringEntryProto(key="columns", value=str(feature_columns)))

    serialized_proto: bytes = proto.SerializeToString()
    main_schema.ml_model_service.load_ml_model(data=serialized_proto, metadata=None, filename=filepath.as_posix())


# pylint: enable=too-many-locals, too-many-statements, too-complex, cell-var-from-loop


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
