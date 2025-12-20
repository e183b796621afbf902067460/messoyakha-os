# pylint: disable=duplicate-code, too-many-lines
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
    compute_global_weights,
    compute_group_weights,
    determine_matching_columns,
    matching_mean,
    matching_mean_by_weights,
    matching_weighted_mean,
    matching_weighted_mean_by_weights,
    quantile_matching_fit,
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


# pylint: disable=too-many-locals, too-many-statements
def _main(main_schema: _MainSchema) -> None:  # noqa: WPS213
    if main_schema.ma_service.ma is None:
        raise FileNotFoundError("There is no moving averages data.")
    ma_booleans: list[str] = main_schema.ma_service.get_ma_booleans(ma=main_schema.ma_service.ma)
    main_schema.ma_service.ma = main_schema.ma_service.ma[
        ["exchange", "section", "ticker", "interval", "datetime"] + ma_booleans
    ]

    if main_schema.adx_service.adx is None:
        raise FileNotFoundError("There is no ADX data.")
    adx_columns: list[str] = main_schema.adx_service.get_adx_columns(
        columns=main_schema.adx_service.adx.columns.tolist()
    )

    if main_schema.ev_service.ev is None:
        raise FileNotFoundError("There is no trades data.")
    logger.info(f"Shape of EV is {main_schema.ev_service.ev.shape}.")

    data: DataFrame = main_schema.ev_service.ev.merge(
        right=main_schema.ma_service.ma, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )
    data = data.merge(
        right=main_schema.adx_service.adx, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )
    data["datetime"] = to_datetime(data["datetime"])
    data["year"] = data["datetime"].dt.year
    data.dropna(inplace=True)

    data["ticks"] = log1p(data["ticks"])  # noqa: WPS204
    data["ticks"] = main_schema.scaler.fit_transform(X=vstack(tup=data["ticks"])).flatten()

    data["matching_columns"] = data.apply(
        lambda row: determine_matching_columns(
            row=row,
            ma_prefixes=main_schema.ma_service.ma_prefixes,  # type: ignore[arg-type]
            potential_columns=adx_columns,
        ),
        axis=1,
    )
    data["matching_columns_encoded"] = data["matching_columns"].astype(str).astype("category")  # noqa: WPS204
    data["matching_columns_length"] = data["matching_columns"].apply(len)
    matching_columns_encoded: list[str] = sorted(data["matching_columns_encoded"].unique().tolist())
    main_schema.encoder.fit(y=matching_columns_encoded)
    encodes: dict[str, int] = {
        matching_column_encoded: int(main_schema.encoder.transform(y=[matching_column_encoded])[0])
        for matching_column_encoded in matching_columns_encoded
    }
    data["matching_columns_encoded"] = data["matching_columns_encoded"].apply(
        lambda matching_column_encoded: encodes[matching_column_encoded]
    )
    data["matching_columns_encoded"] = data["matching_columns_encoded"].astype(int)

    # pylint: disable=cell-var-from-loop
    for adx_column in adx_columns:  # noqa: WPS426
        data[f"is_{adx_column}"] = data["matching_columns"].apply(
            lambda matching_columns: 1 if adx_column in matching_columns else 0
        )
    # pylint: disable=cell-var-from-loop

    data["rank"] = data.apply(
        lambda row: quantile_matching_fit(
            row=row, target_column="ticks", matching_columns=row["matching_columns"]  # noqa: WPS204
        ),
        axis=1,
    )
    data.dropna(subset=["rank"], inplace=True)
    logger.info(f"R2 between target and QMF is {r2_score(y_true=data['ticks'], y_pred=data['rank'])} {data.shape}.")

    train, _, _, _ = train_test_split(
        data, data[["rank"]], train_size=settings.TRAIN_SIZE, random_state=settings.RANDOM_STATE, shuffle=False
    )
    global_weights: dict[str, int] = compute_global_weights(data=train, matching_columns=adx_columns)
    matching_encode_weights: dict[int, dict[str, int]] = compute_group_weights(
        data=train, grouping_column="matching_columns_encoded", matching_columns=adx_columns
    )
    matching_length_weights: dict[int, dict[str, int]] = compute_group_weights(
        data=train, grouping_column="matching_columns_length", matching_columns=adx_columns
    )

    data["matching_mean"] = data.apply(
        lambda row: matching_mean(row=row, matching_columns=row["matching_columns"]), axis=1
    )
    data["matching_weighted_mean"] = data.apply(
        lambda row: matching_weighted_mean(
            row=row,
            weights=global_weights,
            matching_columns=row["matching_columns"],
        ),
        axis=1,
    )

    data["matching_mean_by_encode"] = data.apply(
        lambda row: matching_mean_by_weights(
            row=row,
            weights=matching_encode_weights,
            grouping_column="matching_columns_encoded",
            matching_columns=row["matching_columns"],
        ),
        axis=1,
    )
    data["matching_weighted_mean_by_encode"] = data.apply(
        lambda row: matching_weighted_mean_by_weights(
            row=row,
            weights=matching_encode_weights,
            grouping_column="matching_columns_encoded",
            matching_columns=row["matching_columns"],
        ),
        axis=1,
    )

    data["matching_mean_by_length"] = data.apply(
        lambda row: matching_mean_by_weights(
            row=row,
            weights=matching_length_weights,
            grouping_column="matching_columns_length",
            matching_columns=row["matching_columns"],
        ),
        axis=1,
    )
    data["matching_weighted_mean_by_length"] = data.apply(
        lambda row: matching_weighted_mean_by_weights(
            row=row,
            weights=matching_length_weights,
            grouping_column="matching_columns_length",
            matching_columns=row["matching_columns"],
        ),
        axis=1,
    )

    matching_aggregated_columns: list[str] = [
        column for column in data.columns.tolist() if column.startswith("matching")
    ]
    matching_aggregated_columns.remove("matching_columns")
    matching_aggregated_columns.remove("matching_columns_encoded")
    matching_aggregated_columns.remove("matching_columns_length")
    data["matching_aggregated_mean"] = data.apply(
        lambda row: matching_mean(row=row, matching_columns=matching_aggregated_columns), axis=1
    )

    data["rank"] = data.apply(
        lambda row: quantile_matching_fit(
            row=row, target_column="ticks", matching_columns=matching_aggregated_columns + ["matching_aggregated_mean"]
        ),
        axis=1,
    )
    data.dropna(subset=["rank"], inplace=True)
    logger.info(f"R2 between target and QMF is {r2_score(y_true=data['ticks'], y_pred=data['rank'])} {data.shape}.")

    categorical_features: list[str] = [column for column in data.columns.tolist() if column.startswith("is")] + [
        "matching_columns_length",
        "matching_columns_encoded",
    ]
    feature_columns: list[str] = (
        adx_columns
        + categorical_features
        + [
            "matching_mean",
            "matching_weighted_mean",
            "matching_mean_by_encode",
            "matching_weighted_mean_by_encode",
            "matching_mean_by_length",
            "matching_weighted_mean_by_length",
            "matching_aggregated_mean",
        ]
    )
    data.dropna(subset=feature_columns, inplace=True)
    logger.info(f"Shape of data is {data.shape}.")
    logger.info(f"Total number of features is {len(feature_columns)}.")

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
            "learning_rate": trial.suggest_float("learning_rate", 1e-3, 1e-1, log=True),  # noqa: WPS432
            "iterations": trial.suggest_int("iterations", 2**10, 2**12),  # noqa: WPS432
            "depth": trial.suggest_int("depth", 6, 12),  # noqa: WPS432
            "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 2**2, 2**4),
        }
        optuna_model: CatBoostRegressor = CatBoostRegressor(
            **params,
            loss_function="RMSE",
            eval_metric="RMSE",
            custom_metric=["RMSE"],
            random_state=settings.RANDOM_STATE,
            verbose=False,
        )
        optuna_model.fit(X=train_pool, eval_set=test_pool, use_best_model=True, verbose=False)
        return float(optuna_model.get_best_score()["validation"]["RMSE"])

    study: Study = create_study(direction="minimize", sampler=CmaEsSampler(seed=settings.RANDOM_STATE))
    study.optimize(func=objective, n_trials=10, gc_after_trial=True, show_progress_bar=True)

    model: CatBoostRegressor = CatBoostRegressor(
        **study.best_params,
        loss_function="RMSE",
        eval_metric="RMSE",
        random_seed=settings.RANDOM_STATE,
        use_best_model=True,
        verbose=False,
    )
    model.fit(X=train_pool, eval_set=test_pool, use_best_model=True, verbose=False)

    filepath: Path = Path(f"{uuid1()}.onnx")
    model.save_model(fname=filepath.as_posix(), format="onnx", pool=train_pool)
    proto: ModelProto = load_model(f=filepath.as_posix())
    filepath.unlink()

    proto.metadata_props.append(StringStringEntryProto(key="columns", value=str(feature_columns)))
    proto.metadata_props.append(StringStringEntryProto(key="encodes", value=str(encodes)))

    proto.metadata_props.append(StringStringEntryProto(key="global_weights", value=str(global_weights)))
    proto.metadata_props.append(StringStringEntryProto(key="encode_weights", value=str(matching_encode_weights)))
    proto.metadata_props.append(StringStringEntryProto(key="length_weights", value=str(matching_length_weights)))

    serialized_proto: bytes = proto.SerializeToString()
    main_schema.ml_model_service.load_ml_model(data=serialized_proto, metadata=None, filename=filepath.as_posix())


# pylint: enable=too-many-locals, too-many-statements


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
