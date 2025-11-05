# pylint: disable=duplicate-code
from typing import Final

from boto3 import Session
from catboost import CatBoostRegressor, Pool
from duckdb import DuckDBPyConnection
from numpy import log, log1p, median, ndarray, vstack
from numpy.ma import masked_invalid
from optuna import Study, Trial, create_study
from pandas import DataFrame, Series, to_datetime  # noqa: WPS347
from pydantic import BaseModel
from scipy.special import kl_div
from scipy.stats import boxcox
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.indicators import ADXRepository
from src.adapters.repositories.trades import TradesRepository
from src.schemas.filters import (
    ADXPathParametersSchema,
    ADXQueryParametersSchema,
    TradePathParametersSchema,
    TradeQueryParametersSchema,
)
from src.services.domain.s3 import ADXService, ROIService
from src.services.quantile import identify_nearest, quantile_matching_fit
from src.settings import settings

_RANDOM_SEED: Final[int] = 42
_TEST_SIZE: Final[float] = 0.2


# TODO: add field_validator for data field
class _BoxCoxTransform(BaseModel):
    data: ndarray
    lambda_optimizer: float

    class Config:
        arbitrary_types_allowed = True

    # pylint: disable=redefined-outer-name
    @staticmethod
    def from_boxcox(boxcox: tuple[ndarray, float]) -> "_BoxCoxTransform":
        return _BoxCoxTransform(data=boxcox[0], lambda_optimizer=boxcox[1])

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

    adx: DataFrame | None = adx_service.extract_adx()
    if adx is None:
        raise FileNotFoundError("There is no average directional indexes data.")
    adx.drop_duplicates(inplace=True)

    roi: DataFrame | None = roi_service.extract_roi()
    if roi is None:
        raise FileNotFoundError("There is no trades data.")
    roi.drop_duplicates(inplace=True)

    roi = roi.merge(right=adx, how="left", on=["exchange", "section", "ticker", "interval", "datetime"])
    roi["datetime"] = to_datetime(roi["datetime"])
    roi["year"] = roi["datetime"].dt.year
    roi.dropna(inplace=True)

    roi["ticks"] = log1p(roi["ticks"])
    scaled_target: ndarray = MinMaxScaler().fit_transform(X=vstack(tup=roi["ticks"]))

    features_data: list[dict[str, float]] | DataFrame = []
    for column in roi.columns.tolist():
        if column.startswith("adx"):
            roi[column] = abs(log(roi[column]))
            scaled_feature: ndarray = MinMaxScaler().fit_transform(X=vstack(tup=roi[column]))

            divergence: ndarray = kl_div(scaled_target, scaled_feature)
            divergence = divergence[~masked_invalid(a=divergence).mask]  # type: ignore[no-untyped-call]

            feature_data: dict[str, float] = {"column": column, "divergence": float(median(a=divergence))}

            features_data.append(feature_data)
    features: DataFrame = DataFrame(data=features_data)

    top_percentile: float = features["divergence"].quantile(0.1)
    features.query(f"divergence < {top_percentile}", inplace=True)

    roi["qmf"] = quantile_matching_fit(
        a=roi["ticks"].values, b=roi[features["column"].values.tolist()].values.flatten().tolist()  # noqa: WPS221
    )
    roi["rank"] = roi.apply(
        lambda row: identify_nearest(
            value=row.qmf, values=[row[feature] for feature in features["column"].values.tolist()], rank=1
        ),
        axis=1,
    )

    train: DataFrame = roi.query(f"year < {settings.TRIGGER_DATE.year - 1}")
    scaler: MinMaxScaler = MinMaxScaler()
    boxcox_transform: _BoxCoxTransform = _BoxCoxTransform.from_boxcox(boxcox=boxcox(x=train["rank"]))

    numerical_columns: list[str] = [
        column for column in roi.columns.tolist() if column.startswith("adx")  # noqa: WPS441
    ]
    categorical_columns: list[str] = ["is_long"]

    X_train, X_test, y_train, y_test = train_test_split(
        train[numerical_columns + categorical_columns],
        scaler.fit_transform(X=vstack(Series(boxcox_transform.data))),
        test_size=_TEST_SIZE,
        random_state=_RANDOM_SEED,
    )
    train_pool: Pool = Pool(data=X_train, label=y_train, cat_features=categorical_columns)
    test_pool: Pool = Pool(data=X_test, label=y_test, cat_features=categorical_columns)

    def objective(trial: Trial) -> float:
        params = {
            "rsm": trial.suggest_float("rsm", 0.1, 0.9),  # noqa: WPS432
            "learning_rate": trial.suggest_float("learning_rate", 1e-5, 0.5, log=True),  # noqa: WPS432
            "depth": trial.suggest_int("depth", 4, 8),  # noqa: WPS432
            "iterations": trial.suggest_int("iterations", 500, 1000),  # noqa: WPS432
        }

        train_model: CatBoostRegressor = CatBoostRegressor(
            **params,
            loss_function="MultiQuantile:alpha=0.15, 0.85",
            eval_metric="MultiQuantile:alpha=0.15, 0.85",
            random_seed=_RANDOM_SEED,
            custom_metric=["R2", "MAPE", "MAE"],
            use_best_model=True,
            verbose=False,
        )
        train_model.fit(train_pool, eval_set=test_pool, use_best_model=True, verbose=False)
        return float(train_model.get_best_score()["validation"]["MAE"])

    study: Study = create_study(direction="minimize")
    study.optimize(objective, n_trials=10, gc_after_trial=True, show_progress_bar=True)

    validation: DataFrame = roi.query(f"year >= {settings.TRIGGER_DATE.year - 1}")
    boxcox_target: ndarray = boxcox(x=validation["rank"], lmbda=boxcox_transform.lambda_optimizer)
    validation_pool: Pool = Pool(
        data=validation[numerical_columns + categorical_columns],
        label=scaler.transform(X=vstack(Series(boxcox_target))),
        cat_features=categorical_columns,
    )

    test_model: CatBoostRegressor = CatBoostRegressor(
        **study.best_params,
        loss_function="MultiQuantile:alpha=0.15, 0.85",
        eval_metric="MultiQuantile:alpha=0.15, 0.85",
        random_seed=_RANDOM_SEED,
        custom_metric=["R2", "MAPE", "MAE"],
        use_best_model=True,
        verbose=False,
    )
    test_model.fit(train_pool, eval_set=test_pool, use_best_model=True, verbose=False)
    assert test_model.is_fitted()  # noqa: S101


# pylint: enable=duplicate-code
