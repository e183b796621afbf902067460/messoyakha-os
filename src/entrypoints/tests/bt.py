# pylint: disable=duplicate-code, too-many-lines
from warnings import filterwarnings
from typing import Final
from secrets import randbelow

from backtesting import Backtest
from boto3 import Session
from duckdb import DuckDBPyConnection
from loguru import logger
from pandas import DataFrame, to_datetime, Series  # noqa: WPS347
from pydantic import BaseModel
from sklearn.model_selection import train_test_split
from talib import SAREXT

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.indicators import ADXRepository, MARepository
from src.adapters.repositories.trials import SARTrialsRepository
from src.schemas.filters import (
    ADXPathParametersSchema,
    ADXQueryParametersSchema,
    MAPathParametersSchema,
    MAQueryParametersSchema,
    MLModelPathParametersSchema,
    MLModelQueryParametersSchema,
    OHLCPathParametersSchema,
    OHLCQueryParametersSchema,
    SARTrialPathParametersSchema,
    SARTrialQueryParametersSchema
)
from src.schemas.trials import SARParametersSchema
from src.schemas.backtests import BacktestParametersSchema
from src.services.domain.s3 import ADXService, OHLCService, MAService, MLModelService, SARService
from src.services.trends import MLTrendStrategy
from src.settings import settings

filterwarnings("ignore")

_THRESHOLD: Final[float] = 0.8


class _MainSchema(BaseModel):
    ohlc_service: OHLCService
    ma_service: MAService
    adx_service: ADXService
    sar_service: SARService

    ml_model_service: MLModelService

    class Config:
        arbitrary_types_allowed = True


# pylint: disable=too-many-locals, too-many-statements, too-complex, cell-var-from-loop, protected-access
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

    if main_schema.adx_service.adx is None:
        raise FileNotFoundError("There is no ADX data.")

    if main_schema.sar_service.sar_trials is None:
        raise FileNotFoundError("There is no trials data.")

    thresholded_metric: float = main_schema.sar_service.sar_trials["value"].quantile(_THRESHOLD)
    logger.info(f"Thresholded lowest metric is {thresholded_metric}.")

    main_schema.sar_service.sar_trials.query(f"value > {thresholded_metric}", inplace=True)
    logger.info(f"Total unique parameters number is {len(main_schema.sar_service.sar_trials)}.")

    if main_schema.ml_model_service.ml_model is None:
        raise FileNotFoundError("There is no saved model file.")

    data: DataFrame = main_schema.ohlc_service.ohlc.merge(
        right=main_schema.ma_service.ma, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )
    data = data.merge(
        right=main_schema.adx_service.adx, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )
    logger.info(f"The end of data is {data['datetime'].max()}.")

    data["datetime"] = to_datetime(data["datetime"])
    data["year"] = data["datetime"].dt.year

    parameters_index: int = randbelow(exclusive_upper_bound=len(main_schema.sar_service.sar_trials))
    parameters_schema: SARParametersSchema = SARParametersSchema(
        **main_schema.sar_service.sar_trials.iloc[parameters_index].to_dict()
    )
    data["sar"] = SAREXT(high=data["High"], low=data["Low"], **parameters_schema.model_dump(by_alias=True))
    data["sar"] = abs(data["sar"])

    _, test, _, _ = train_test_split(
        data,
        data[["sar"]],
        train_size=settings.TRAIN_SIZE,
        random_state=settings.RANDOM_STATE,
        shuffle=False,
    )
    test.set_index(keys="datetime", inplace=True)

    backtest: Backtest = Backtest(
        data=test,
        strategy=MLTrendStrategy,
        trade_on_close=False,
        hedging=False,
        finalize_trades=True,
        exclusive_orders=True,
        **BacktestParametersSchema().model_dump(),
    )

    # pylint: disable=protected-access
    backtest._strategy.ml_model = main_schema.ml_model_service.ml_model
    backtest._strategy.ma_prefixes = main_schema.ma_service.ma_prefixes
    # pylint: enable=protected-access

    statistics: Series = backtest.run()
    statistics["_trades"]["Ticks"] = statistics["_trades"]["ExitBar"] - statistics["_trades"]["EntryBar"]
    statistics["_trades"]["IsLong"] = (statistics["_trades"]["Size"] > 0).astype(int)
    statistics.to_csv("statistics.csv")
    statistics["_trades"].to_csv("trades.csv", index=False)
    backtest.plot()


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
