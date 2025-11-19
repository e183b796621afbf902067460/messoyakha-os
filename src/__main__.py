# pylint: disable=duplicate-code
from secrets import randbelow

from backtesting import Backtest
from boto3 import Session
from duckdb import DuckDBPyConnection
from loguru import logger
from onnxruntime import InferenceSession
from pandas import DataFrame, Series, to_datetime  # noqa: WPS347
from talib import SAREXT

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.indicators import ADXRepository, MARepository
from src.adapters.repositories.trials import SARTrialsRepository
from src.schemas.backtests import BacktestParametersSchema
from src.schemas.domain.s3 import GetObjectResponseSchema
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
    SARTrialQueryParametersSchema,
)
from src.schemas.trials import SARParametersSchema
from src.services.domain.s3 import ADXService, MAService, MLModelService, OHLCService, SARService
from src.services.statistic import weighted_average_by
from src.services.trend import MA, MLTrendStrategy
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
    adx_service: ADXService = ADXService(
        s3_client=s3_client,
        repository=ADXRepository(connection=duckdb_connection),
        query_parameters=ADXQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=ADXPathParametersSchema(bucket=settings.S3_BUCKET, directory="average-directional-indexes"),
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
    ml_model_service: MLModelService = MLModelService(
        s3_client=s3_client,
        query_parameters=MLModelQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=MLModelPathParametersSchema(bucket=settings.S3_BUCKET, directory="models"),
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

    average_directional_indexes: DataFrame | None = adx_service.extract_adx()
    if average_directional_indexes is None:
        raise FileNotFoundError("There is no average directional indexes data.")
    average_directional_indexes.drop_duplicates(inplace=True)

    trials: DataFrame | None = sar_service.extract_sar()
    if trials is None:
        raise FileNotFoundError("There is no trials data.")
    trials.drop_duplicates(inplace=True)
    stochastic_parameters_index: int = randbelow(exclusive_upper_bound=int(0.025 * len(trials)))  # noqa: WPS432

    ohlc = ohlc.merge(right=moving_averages, how="left", on=["exchange", "section", "ticker", "interval", "datetime"])
    ohlc = ohlc.merge(
        right=average_directional_indexes, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )
    ohlc.dropna(
        subset=[
            f"{MA}_open",
            f"{MA}_high",
            f"{MA}_low",
            f"{MA}_close",
        ],
        inplace=True,
    )

    parameters_schema: SARParametersSchema = SARParametersSchema(**trials.iloc[stochastic_parameters_index].to_dict())
    ohlc["sar"] = SAREXT(
        high=ohlc[f"{MA}_high"],
        low=ohlc[f"{MA}_low"],
        **parameters_schema.model_dump(by_alias=True),
    )
    ohlc["sar"] = abs(ohlc["sar"])

    ml_model_response_schema: GetObjectResponseSchema = ml_model_service.extract_ml_model()
    ml_model_inference_session: InferenceSession = InferenceSession(ml_model_response_schema.body.read())

    for multiplier in ml_model_response_schema.metadata["multipliers"]:
        ohlc = weighted_average_by(
            dataframe=ohlc,
            columns=list(ml_model_response_schema.metadata["weights"].keys()),
            multiplier=multiplier,
            weights=ml_model_response_schema.metadata["weights"],
        )
        logger.info(f"{multiplier} multiplier is ready.")

    ohlc["datetime"] = to_datetime(ohlc["datetime"])
    ohlc["year"] = ohlc["datetime"].dt.year
    ohlc.query(f"year >= {settings.TRIGGER_DATE.year - 1}", inplace=True)
    ohlc.set_index(keys="datetime", inplace=True)
    ohlc.dropna(inplace=True)

    test: Backtest = Backtest(
        data=ohlc,
        strategy=MLTrendStrategy,
        trade_on_close=False,
        hedging=False,
        finalize_trades=False,
        exclusive_orders=True,
        **BacktestParametersSchema().model_dump(),
    )

    # pylint: disable=protected-access
    test._strategy.ml_model_inference_session = ml_model_inference_session
    test._strategy.ml_model_response_schema = ml_model_response_schema

    # pylint: enable=protected-access

    statistics: Series = test.run(
        sar_on_bull_market_prefix="sar",
        ma_on_bull_market_prefix=MA,
        sar_on_bear_market_prefix="sar",
        ma_on_bear_market_prefix=MA,
    )
    statistics["_trades"]["Ticks"] = statistics["_trades"]["ExitBar"] - statistics["_trades"]["EntryBar"]
    statistics["_trades"]["IsLong"] = (statistics["_trades"]["Size"] > 0).astype(int)
    statistics.to_csv("statistics.csv")
    statistics["_trades"].to_csv("trades.csv", index=False)
    test.plot()


# pylint: enable=duplicate-code
