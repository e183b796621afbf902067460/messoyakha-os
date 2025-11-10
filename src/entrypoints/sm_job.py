# pylint: disable=duplicate-code
from itertools import product
from typing import Final
from warnings import filterwarnings

from boto3 import Session
from collinearity import SelectNonCollinear
from duckdb import DuckDBPyConnection
from lightgbm import LGBMRegressor
from loguru import logger
from numpy import array, average, log, log1p, median, ndarray, vstack
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
from src.services.quantile import identify_nearest, quantile_matching_fit
from src.settings import settings

filterwarnings("ignore")

_RANDOM_SEED: Final[int] = 42
_TEST_SIZE: Final[float] = 0.2


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

    roi: DataFrame | None = roi_service.extract_roi()
    if roi is None:
        raise FileNotFoundError("There is no trades data.")
    roi.drop_duplicates(inplace=True)

    roi = roi.merge(right=adx, how="left", on=["exchange", "section", "ticker", "interval", "datetime"])
    roi["datetime"] = to_datetime(roi["datetime"])
    roi["year"] = roi["datetime"].dt.year
    roi.dropna(inplace=True)

    roi["ticks"] = log1p(roi["ticks"])
    train: DataFrame = roi.query(f"year < {settings.TRIGGER_DATE.year - 1}")
    validation: DataFrame = roi.query(f"year >= {settings.TRIGGER_DATE.year - 1}")

    target_scaler: MinMaxScaler = MinMaxScaler()

    optimizer: float
    train["ticks"], optimizer = boxcox(x=train["ticks"])  # noqa: WPS414
    train["ticks"] = target_scaler.fit_transform(X=vstack(tup=train["ticks"])).flatten()
    validation["ticks"] = boxcox(x=validation["ticks"], lmbda=optimizer)
    validation["ticks"] = target_scaler.transform(X=vstack(tup=validation["ticks"])).flatten()

    divergences: DataFrame = DataFrame()

    numerical_columns: list[str] = [column for column in roi.columns.tolist() if column.startswith("adx")]
    for column in numerical_columns:  # noqa: WPS426
        train[column] = abs(log(train[column]))
        validation[column] = abs(log(validation[column]))

        adx_scaler: MinMaxScaler = MinMaxScaler()

        train[column] = adx_scaler.fit_transform(X=vstack(tup=train[column])).flatten()
        validation[column] = adx_scaler.transform(X=vstack(tup=validation[column])).flatten()
        validation[column] = validation.apply(lambda row: min(row[column], 1), axis=1)  # noqa: B023

        divergence: ndarray = kl_div(train["ticks"].values, train[column].values)
        divergence = divergence[~masked_invalid(a=divergence).mask]  # type: ignore[no-untyped-call]
        divergences = concat(
            objs=[divergences, DataFrame(data=[{"column": column, "divergence": float(median(a=divergence))}])]
        )
    divergences.query(f"divergence < {divergences['divergence'].quantile(0.2)}", inplace=True)  # noqa: WPS432
    numerical_columns = divergences["column"].values.tolist()

    train["qmf"] = quantile_matching_fit(
        a=train["ticks"].values, b=train[numerical_columns].values.flatten().tolist()  # noqa: WPS221
    )
    validation["qmf"] = quantile_matching_fit(
        a=validation["ticks"].values, b=train[numerical_columns].values.flatten().tolist()  # noqa: WPS221
    )
    train["rank"] = train.apply(
        lambda row: identify_nearest(value=row["qmf"], values=[row[feature] for feature in numerical_columns], rank=1),
        axis=1,
    )
    validation["rank"] = validation.apply(
        lambda row: identify_nearest(value=row["qmf"], values=[row[feature] for feature in numerical_columns], rank=1),
        axis=1,
    )

    weights: dict[str, int] = (
        train.apply(lambda row: _identify_rank(row=row, quantile_columns=numerical_columns), axis=1)
        .value_counts()
        .to_dict()
    )
    for first_numerical_column, second_numerical_column in product(  # noqa: WPS426
        numerical_columns, numerical_columns
    ):
        if first_numerical_column != second_numerical_column:
            adx_numerical_column: str = (
                str(sorted([first_numerical_column, second_numerical_column]))
                .replace("[", "")
                .replace("]", "")
                .replace("'", "")
                .replace(",", "")
            )

            adx_weighted_numerical_column: str = "weighted" + adx_numerical_column
            adx_average_numerical_column: str = "average" + adx_numerical_column

            columns: list[str] = train.columns.tolist()
            if adx_weighted_numerical_column not in columns and adx_average_numerical_column not in columns:
                train[adx_weighted_numerical_column] = train.apply(
                    lambda row: average(
                        a=[row[first_numerical_column], row[second_numerical_column]],
                        weights=[weights[first_numerical_column], weights[second_numerical_column]],
                    ),
                    axis=1,
                )
                train[adx_average_numerical_column] = train.apply(
                    lambda row: average(
                        a=[row[first_numerical_column], row[second_numerical_column]],
                    ),
                    axis=1,
                )

                validation[adx_weighted_numerical_column] = validation.apply(
                    lambda row: average(
                        a=[row[first_numerical_column], row[second_numerical_column]],
                        weights=[weights[first_numerical_column], weights[second_numerical_column]],
                    ),
                    axis=1,
                )
                validation[adx_average_numerical_column] = validation.apply(
                    lambda row: average(
                        a=[row[first_numerical_column], row[second_numerical_column]],
                    ),
                    axis=1,
                )

    columns = train.columns.tolist()

    numerical_columns = []
    for prefix in ["weighted", "average"]:  # noqa: WPS335
        collinear_columns: list[str] = [
            collinear_column for collinear_column in columns if collinear_column.startswith(prefix)
        ]
        collinear_values: ndarray = train[collinear_columns].values

        selector: SelectNonCollinear = SelectNonCollinear(
            correlation_threshold=0.95, scoring=f_regression  # noqa: WPS432
        )
        selector.fit(X=collinear_values)

        numerical_columns.extend(array(collinear_columns)[selector.get_support()].tolist())

    logger.info(f"Total number of features is {len(numerical_columns)}.")

    train["rank"] = train.apply(
        lambda row: identify_nearest(
            value=row["ticks"], values=[row[feature] for feature in numerical_columns], rank=1
        ),
        axis=1,
    )
    validation["rank"] = validation.apply(
        lambda row: identify_nearest(
            value=row["ticks"], values=[row[feature] for feature in numerical_columns], rank=1
        ),
        axis=1,
    )

    X_train, X_test, y_train, y_test = train_test_split(
        train[numerical_columns],
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
            **params, objective="mae", eval_metric="mae", random_seed=_RANDOM_SEED, metric=["mae"], verbosity=-1
        )
        model.fit(X=X_train, y=y_train, eval_set=[(X_test, y_test)])
        return float(model.best_score_["valid_0"].get("l1"))

    study: Study = create_study(direction="minimize")
    study.optimize(objective, n_trials=10, gc_after_trial=True, show_progress_bar=True)

    test_model: LGBMRegressor = LGBMRegressor(
        **study.best_params, objective="mae", eval_metric="mae", random_seed=_RANDOM_SEED, metric=["mae"], verbosity=-1
    )
    test_model.fit(X=X_train, y=y_train, eval_set=[(X_test, y_test)])

    validation["y"] = test_model.predict(validation[numerical_columns])
    validation.to_csv("data.csv", index=False)


# pylint: enable=duplicate-code,too-complex,cell-var-from-loop
