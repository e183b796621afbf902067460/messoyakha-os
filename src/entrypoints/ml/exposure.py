# pylint: disable=duplicate-code
from typing import Final
from uuid import uuid1
from warnings import filterwarnings

from boto3 import Session
from duckdb import DuckDBPyConnection
from lightgbm import LGBMRegressor
from loguru import logger
from numpy import log1p, median, ndarray, vstack
from numpy.ma import masked_invalid
from onnx import ModelProto, StringStringEntryProto
from onnxconverter_common.data_types import FloatTensorType
from onnxmltools import convert_lightgbm
from optuna import Study, Trial, create_study
from pandas import DataFrame, Series, concat, to_datetime  # noqa: WPS347
from scipy.special import inv_boxcox, kl_div
from scipy.stats import boxcox
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.indicators import ADXRepository, RatioRepository
from src.adapters.repositories.trades import TradesRepository
from src.schemas.filters import (
    ADXPathParametersSchema,
    ADXQueryParametersSchema,
    MLModelPathParametersSchema,
    MLModelQueryParametersSchema,
    RatioPathParametersSchema,
    RatioQueryParametersSchema,
    TradePathParametersSchema,
    TradeQueryParametersSchema,
)
from src.services.domain.s3 import ADXService, MLModelService, RatioService, ROIService
from src.services.statistic import qq, weighted_average_by
from src.services.target import TargetEngineeringService
from src.settings import settings

filterwarnings("ignore")

_RANDOM_SEED: Final[int] = 42
_TEST_SIZE: Final[float] = 0.2

_DIVERGENCE_THRESHOLD: Final[float] = 0.1
_CORRELATION_THRESHOLD: Final[float] = 0.5
_RANGE: Final[int] = 3

_TICKS_WEIGHT: Final[int] = 10
_RANK_WEIGHT: int = 100 - _TICKS_WEIGHT


# pylint: disable=too-complex,cell-var-from-loop
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
    ratio_service: RatioService = RatioService(
        s3_client=s3_client,
        repository=RatioRepository(connection=duckdb_connection),
        query_parameters=RatioQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=RatioPathParametersSchema(bucket=settings.S3_BUCKET, directory="ratios"),
    )
    adx_service: ADXService = ADXService(
        s3_client=s3_client,
        repository=ADXRepository(connection=duckdb_connection),
        query_parameters=ADXQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=ADXPathParametersSchema(bucket=settings.S3_BUCKET, directory="average-directional-indexes"),
    )
    roi_service: ROIService = ROIService(
        s3_client=s3_client,
        repository=TradesRepository(connection=duckdb_connection),
        query_parameters=TradeQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=TradePathParametersSchema(bucket=settings.S3_BUCKET, directory="trades"),
    )
    ml_model_service: MLModelService = MLModelService(
        s3_client=s3_client,
        query_parameters=MLModelQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=MLModelPathParametersSchema(bucket=settings.S3_BUCKET, directory="exposure"),
    )

    adx: DataFrame | None = adx_service.extract_adx()
    if adx is None:
        raise FileNotFoundError("There is no average directional indexes data.")
    adx.drop_duplicates(inplace=True)
    adx_columns: list[str] = [adx_column for adx_column in adx.columns.tolist() if adx_column.startswith("adx")]

    ratios: DataFrame | None = ratio_service.extract_ratio()
    if ratios is None:
        raise FileNotFoundError("There is no ratios data.")
    ratios.drop_duplicates(inplace=True)
    ratio_columns: list[str] = [
        ratio_column for ratio_column in adx.columns.tolist() if ratio_column.startswith("ratio")
    ]

    roi: DataFrame | None = roi_service.extract_roi()
    if roi is None:
        raise FileNotFoundError("There is no trades data.")
    roi.drop_duplicates(inplace=True)
    logger.info(f"Shape of ROI is {roi.shape}.")

    roi = roi.merge(right=adx, how="left", on=["exchange", "section", "ticker", "interval", "datetime"])
    roi = roi.merge(right=ratios, how="left", on=["exchange", "section", "ticker", "interval", "datetime"])
    roi["datetime"] = to_datetime(roi["datetime"])
    roi["year"] = roi["datetime"].dt.year
    roi.dropna(inplace=True)

    train: DataFrame = roi.query(f"year < {settings.TRIGGER_DATE.year - 1}")
    validation: DataFrame = roi.query(f"year >= {settings.TRIGGER_DATE.year - 1}")

    target_scaler: MinMaxScaler = MinMaxScaler()

    train["ticks"] = log1p(train["ticks"])  # noqa: WPS204
    validation["ticks"] = log1p(validation["ticks"])

    optimizer: float
    train["ticks"], optimizer = boxcox(x=train["ticks"])  # noqa: WPS414
    train["ticks"] = target_scaler.fit_transform(X=vstack(tup=train["ticks"])).flatten()
    validation["ticks"] = boxcox(x=validation["ticks"], lmbda=optimizer)
    validation["ticks"] = target_scaler.transform(X=vstack(tup=validation["ticks"])).flatten()

    target_median: float = train.ticks.quantile(0.5)
    target_median_unscaled: float = target_scaler.inverse_transform(X=vstack(tup=[target_median]))
    target_median_inverse: float = inv_boxcox(target_median_unscaled, optimizer)[0][0]
    logger.info(f"Target median is {target_median} ({target_median_inverse}).")

    divergences: DataFrame = DataFrame()
    for adx_column in adx_columns:  # noqa: WPS426
        divergence: ndarray = kl_div(train["ticks"].values, train[adx_column].values)
        divergence = divergence[~masked_invalid(a=divergence).mask]  # type: ignore[no-untyped-call]
        divergences = concat(
            objs=[divergences, DataFrame(data=[{"column": adx_column, "divergence": float(median(a=divergence))}])]
        )
    divergences.query(f"divergence < {divergences['divergence'].quantile(_DIVERGENCE_THRESHOLD)}", inplace=True)
    rank_target_columns: list[str] = divergences["column"].values.tolist()

    train["rank"] = train.apply(
        lambda row: qq(tick=row["ticks"], ticks=train["ticks"], q=train[rank_target_columns], row=row),
        axis=1,
    )
    validation["rank"] = validation.apply(
        lambda row: qq(tick=row["ticks"], ticks=train["ticks"], q=validation[rank_target_columns], row=row),
        axis=1,
    )
    logger.info(f"Correlation between target and QMF is {train[['rank', 'ticks']].corr()['rank'].ticks}.")

    ranks: dict[int, TargetEngineeringService] = {}
    for rank in range(1, _RANGE):  # noqa: WPS426
        target_engineering_service: TargetEngineeringService = TargetEngineeringService(
            target_data=train, target_columns=rank_target_columns
        )
        logger.info(f"({rank}) Weights are {target_engineering_service.weights}.")
        logger.info(f"({rank}) Multipliers are {target_engineering_service.multipliers}.")

        for multiplier in target_engineering_service.multipliers:
            train = weighted_average_by(
                dataframe=train, multiplier=multiplier, weights=target_engineering_service.weights
            )
            validation = weighted_average_by(
                dataframe=validation, multiplier=multiplier, weights=target_engineering_service.weights
            )
            logger.info(f"Multiplier {multiplier} is ready.")

        columns: list[str] = [column for column in train.columns.tolist() if "weighted" in column]
        correlations: Series = train[columns + ["rank"]].corr(method="spearman")["rank"].sort_values()
        threshold: float = correlations.quantile(_CORRELATION_THRESHOLD)
        correlations = correlations[correlations > threshold]

        rank_target_columns = correlations.index.tolist()
        rank_target_columns.remove("rank")

        train["rank"] = train.apply(
            lambda row: qq(tick=row["ticks"], ticks=train["ticks"], q=train[rank_target_columns], row=row),
            axis=1,
        )
        validation["rank"] = validation.apply(
            lambda row: qq(tick=row["ticks"], ticks=train["ticks"], q=validation[rank_target_columns], row=row),
            axis=1,
        )
        ranks.update({rank: target_engineering_service})

        logger.info(f"({rank}) Correlation between target and QMF is {train[['rank', 'ticks']].corr()['rank'].ticks}.")

    feature_columns: list[str] = (
        adx_columns
        + ratio_columns
        + [weighted_column for weighted_column in train.columns.tolist() if "weighted" in weighted_column]
    )
    logger.info(f"Total number of features is {len(feature_columns)}.")

    train["rank"] = (train["rank"] * _RANK_WEIGHT + train["ticks"] * _TICKS_WEIGHT) / sum([_TICKS_WEIGHT, _RANK_WEIGHT])
    validation["rank"] = (validation["rank"] * _RANK_WEIGHT + validation["ticks"] * _TICKS_WEIGHT) / sum(
        [_TICKS_WEIGHT, _RANK_WEIGHT]
    )
    logger.info(f"Correlation between target and QMF is {train[['rank', 'ticks']].corr()['rank'].ticks}.")

    X_train, X_test, y_train, y_test = train_test_split(
        train[feature_columns],
        train[["rank"]],
        test_size=_TEST_SIZE,
        random_state=_RANDOM_SEED,
    )

    def objective(trial: Trial) -> float:
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 0.00001, 0.1, log=True),  # noqa: WPS432
            "n_estimators": trial.suggest_int("n_estimators", 2**10, 2**12),  # noqa: WPS432
            "max_depth": trial.suggest_int("max_depth", 2**4, 2**10),  # noqa: WPS432
            "num_leaves": trial.suggest_int("num_leaves", 2**4, 2**10),  # noqa: WPS432
            "reg_lambda": trial.suggest_float("reg_lambda", 0.01, 0.5, log=True),  # noqa: WPS432
            "reg_alpha": trial.suggest_float("reg_alpha", 0.01, 0.5, log=True),  # noqa: WPS432
            "feature_fraction": trial.suggest_float("feature_fraction", 0.1, 0.5),  # noqa: WPS432
            "boosting_type": trial.suggest_categorical("boosting_type", ["rf", "gbdt"]),
        }
        optuna_model: LGBMRegressor = LGBMRegressor(**params, objective="rmse", random_seed=_RANDOM_SEED, verbosity=-1)
        optuna_model.fit(X=X_train, y=y_train, eval_set=[(X_test, y_test)])
        return float(optuna_model.best_score_["valid_0"].get("rmse"))

    study: Study = create_study(direction="minimize")
    study.optimize(func=objective, n_trials=100, gc_after_trial=True, show_progress_bar=True)

    model: LGBMRegressor = LGBMRegressor(
        **study.best_params,
        objective="rmse",
        random_seed=_RANDOM_SEED,
        verbosity=-1,
    )
    model.fit(X=X_train, y=y_train, eval_set=[(X_test, y_test)])

    proto: ModelProto = convert_lightgbm(
        model=model, initial_types=[("input", FloatTensorType([None, len(feature_columns)]))]
    )
    for rank, service in ranks.items():  # noqa: WPS440
        proto.metadata_props.append(StringStringEntryProto(key=f"{rank}_weights", value=str(service.weights)))
        proto.metadata_props.append(StringStringEntryProto(key=f"{rank}_multipliers", value=str(service.multipliers)))
    proto.metadata_props.append(StringStringEntryProto(key="range", value=str(_RANGE)))
    proto.metadata_props.append(StringStringEntryProto(key="columns", value=str(feature_columns)))
    serialized_proto: bytes = proto.SerializeToString()

    validation["y"] = model.predict(validation[feature_columns])
    validation.to_csv("data.csv", index=False)

    ml_model_service.load_ml_model(data=serialized_proto, metadata=None, filename=f"{uuid1()}.onnx")

# pylint: enable=duplicate-code,too-complex,cell-var-from-loop
