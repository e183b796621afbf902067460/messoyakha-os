# pylint: disable=duplicate-code
from itertools import product
from typing import Final
from warnings import filterwarnings

from boto3 import Session
from collinearity import SelectNonCollinear
from duckdb import DuckDBPyConnection
from lightgbm import LGBMRegressor
from loguru import logger
from numpy import argsort, array, isnan, log, log1p, median, ndarray, vstack
from numpy.ma import masked_invalid
from optuna import Study, Trial, create_study
from pandas import DataFrame, Series, concat, to_datetime  # noqa: WPS347
from scipy.special import kl_div
from scipy.stats import boxcox
from sklearn.feature_selection import f_regression
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
from src.services.statistic import quantile_matching_fit, weighted_average_by
from src.settings import settings

filterwarnings("ignore")

_RANDOM_SEED: Final[int] = 42
_TEST_SIZE: Final[float] = 0.2


def _identify_nearest(value: float, values: list[float] | ndarray, rank: int = 0) -> float:
    values = array(object=values)
    values = values[~isnan(values)]

    distances: ndarray = abs(values - value)  # type: ignore[operator, arg-type]
    indices: ndarray = argsort(a=distances)

    return float(values[indices[rank]])


def _identify_rank(row: Series, quantile_columns: list[str]) -> str | None:
    for quantile_column in quantile_columns:
        if row["rank"] == row[quantile_column]:
            return quantile_column
    return None


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
    all_adx_columns: list[str] = [adx_column for adx_column in adx.columns.tolist() if adx_column.startswith("adx")]

    roi: DataFrame | None = roi_service.extract_roi()
    if roi is None:
        raise FileNotFoundError("There is no trades data.")
    roi.drop_duplicates(inplace=True)

    roi = roi.merge(right=adx, how="left", on=["exchange", "section", "ticker", "interval", "datetime"])
    roi["datetime"] = to_datetime(roi["datetime"])
    roi["year"] = roi["datetime"].dt.year
    roi.dropna(inplace=True)

    train: DataFrame = roi.query(f"year < {settings.TRIGGER_DATE.year - 1}")
    validation: DataFrame = roi.query(f"year >= {settings.TRIGGER_DATE.year - 1}")

    target_scaler: MinMaxScaler = MinMaxScaler()

    target_mean: float = train["ticks"].mean()  # noqa: WPS204
    target_std: float = train["ticks"].std()
    target_sigma: float = target_mean + target_std * 3
    train["ticks"] = train["ticks"].apply(lambda tick: tick if tick < target_sigma else target_sigma)
    validation["ticks"] = validation["ticks"].apply(  # noqa: WPS204
        lambda tick: tick if tick < target_sigma else target_sigma
    )

    train["ticks"] = log1p(train["ticks"])
    validation["ticks"] = log1p(validation["ticks"])

    optimizer: float
    train["ticks"], optimizer = boxcox(x=train["ticks"])  # noqa: WPS414
    train["ticks"] = target_scaler.fit_transform(X=vstack(tup=train["ticks"])).flatten()
    validation["ticks"] = boxcox(x=validation["ticks"], lmbda=optimizer)
    validation["ticks"] = target_scaler.transform(X=vstack(tup=validation["ticks"])).flatten()
    logger.info(f"Target median is {train.ticks.median()}.")

    divergences: DataFrame = DataFrame()
    for adx_column in all_adx_columns:  # noqa: WPS426
        train[adx_column] = abs(log(train[adx_column]))
        validation[adx_column] = abs(log(validation[adx_column]))

        adx_scaler: MinMaxScaler = MinMaxScaler()

        train[adx_column] = adx_scaler.fit_transform(X=vstack(tup=train[adx_column])).flatten()
        validation[adx_column] = adx_scaler.transform(X=vstack(tup=validation[adx_column])).flatten()
        validation[adx_column] = validation.apply(
            lambda row: min(row[adx_column], 1) if row[adx_column] > 1 else max(row[adx_column], 0),  # noqa: WPS221
            axis=1,
        )  # noqa: B023

        divergence: ndarray = kl_div(train["ticks"].values, train[adx_column].values)
        divergence = divergence[~masked_invalid(a=divergence).mask]  # type: ignore[no-untyped-call]
        divergences = concat(
            objs=[divergences, DataFrame(data=[{"column": adx_column, "divergence": float(median(a=divergence))}])]
        )
    divergences.query(f"divergence < {divergences['divergence'].quantile(0.2)}", inplace=True)  # noqa: WPS432
    feature_columns: list[str] = divergences["column"].values.tolist()

    train["qmf"] = quantile_matching_fit(
        a=train["ticks"].values, b=train[feature_columns].values.flatten().tolist()  # noqa: WPS221
    )
    validation["qmf"] = quantile_matching_fit(
        a=validation["ticks"].values, b=train[feature_columns].values.flatten().tolist()  # noqa: WPS221
    )
    train["rank"] = train.apply(
        lambda row: _identify_nearest(value=row["qmf"], values=[row[feature] for feature in feature_columns], rank=1),
        axis=1,
    )
    validation["rank"] = validation.apply(
        lambda row: _identify_nearest(value=row["qmf"], values=[row[feature] for feature in feature_columns], rank=1),
        axis=1,
    )

    weights: dict[str, float] = (
        train.apply(lambda row: _identify_rank(row=row, quantile_columns=feature_columns), axis=1)
        .value_counts()
        .to_dict()
    )
    logger.info(f"Weights are {weights}.")

    multipliers: list[int] = [2, 4]
    for multiplier in multipliers:
        train = weighted_average_by(
            dataframe=train, columns=list(weights.keys()), multiplier=multiplier, weights=weights
        )
        validation = weighted_average_by(
            dataframe=validation, columns=list(weights.keys()), multiplier=multiplier, weights=weights
        )
        logger.info(f"{multiplier} multiplier is ready.")

    feature_columns = []
    for prefix, multiplier in product(["weighted", "average"], multipliers):  # noqa: WPS335 WPS440
        collinear_columns: list[str] = [
            collinear_column
            for collinear_column in train.columns.tolist()
            if collinear_column.startswith(f"{multiplier}_{prefix}")
        ]
        collinear_values: ndarray = train[collinear_columns].values

        selector: SelectNonCollinear = SelectNonCollinear(
            correlation_threshold=0.95, scoring=f_regression  # noqa: WPS432
        )
        selector.fit(X=collinear_values)

        feature_columns.extend(array(collinear_columns)[selector.get_support()].tolist())
    feature_columns.extend(all_adx_columns)
    logger.info(f"Total number of features is {len(feature_columns)}.")

    X_train, X_test, y_train, y_test = train_test_split(
        train[feature_columns],
        train[["rank"]],
        test_size=_TEST_SIZE,
        random_state=_RANDOM_SEED,
    )

    def objective(trial: Trial) -> float:
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.5, log=True),  # noqa: WPS432,
            "n_estimators": trial.suggest_int("n_estimators", 1000, 5000),  # noqa: WPS432
            "early_stopping_round": trial.suggest_int("early_stopping_round", 1000, 2000),  # noqa: WPS432
        }
        model: LGBMRegressor = LGBMRegressor(
            **params, objective="rmse", eval_metric="rmse", random_seed=_RANDOM_SEED, metric=["rmse"], verbosity=-1
        )
        model.fit(X=X_train, y=y_train, eval_set=[(X_test, y_test)])
        return float(model.best_score_["valid_0"].get("rmse"))

    study: Study = create_study(direction="minimize")
    study.optimize(objective, n_trials=10, gc_after_trial=True, show_progress_bar=True)

    test_model: LGBMRegressor = LGBMRegressor(
        **study.best_params,
        objective="rmse",
        eval_metric="rmse",
        random_seed=_RANDOM_SEED,
        metric=["rmse"],
        verbosity=-1,
    )
    test_model.fit(X=X_train, y=y_train, eval_set=[(X_test, y_test)])

    validation["y"] = test_model.predict(validation[feature_columns])
    validation.to_csv("data.csv", index=False)


# pylint: enable=duplicate-code,too-complex,cell-var-from-loop
