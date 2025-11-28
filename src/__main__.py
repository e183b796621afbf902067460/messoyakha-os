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
from src.adapters.repositories.indicators import ADXRepository, AroonRepository, MARepository
from src.adapters.repositories.trials import SARTrialsRepository
from src.schemas.backtests import BacktestParametersSchema
from src.schemas.domain.s3 import GetObjectResponseSchema
from src.schemas.filters import (
    ADXPathParametersSchema,
    ADXQueryParametersSchema,
    AroonPathParametersSchema,
    AroonQueryParametersSchema,
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
from src.services.domain.s3 import ADXService, AroonService, MAService, MLModelService, OHLCService, SARService
from src.services.statistic import weighted_average_by
from src.services.trend import MA, MLTrendStrategy
from src.settings import settings

# pylint: disable=too-complex
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
    aroon_service: AroonService = AroonService(
        s3_client=s3_client,
        repository=AroonRepository(connection=duckdb_connection),
        query_parameters=AroonQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=AroonPathParametersSchema(bucket=settings.S3_BUCKET, directory="aroons"),
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
    regression_model_service: MLModelService = MLModelService(
        s3_client=s3_client,
        query_parameters=MLModelQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=MLModelPathParametersSchema(bucket=settings.S3_BUCKET, directory="regression"),
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

    aroons: DataFrame | None = aroon_service.extract_aroon()
    if aroons is None:
        raise FileNotFoundError("There is no aroons data.")
    aroons.drop_duplicates(inplace=True)

    trials: DataFrame | None = sar_service.extract_sar()
    if trials is None:
        raise FileNotFoundError("There is no trials data.")
    trials.drop_duplicates(inplace=True)
    stochastic_parameters_index: int = randbelow(exclusive_upper_bound=int(0.025 * len(trials)))  # noqa: WPS432

    ohlc = ohlc.merge(right=moving_averages, how="left", on=["exchange", "section", "ticker", "interval", "datetime"])
    ohlc = ohlc.merge(
        right=average_directional_indexes, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )
    ohlc = ohlc.merge(right=aroons, how="left", on=["exchange", "section", "ticker", "interval", "datetime"])
    ohlc.dropna(
        subset=[
            f"{MA}_open",
            f"{MA}_high",
            f"{MA}_low",
            f"{MA}_close",
        ],
        inplace=True,
    )
    logger.info(f"The end of data is {ohlc['datetime'].max()}.")

    parameters_schema: SARParametersSchema = SARParametersSchema(**trials.iloc[stochastic_parameters_index].to_dict())
    ohlc["sar"] = SAREXT(
        high=ohlc[f"{MA}_high"],
        low=ohlc[f"{MA}_low"],
        **parameters_schema.model_dump(by_alias=True),
    )
    ohlc["sar"] = abs(ohlc["sar"])

    regression_model_response_schema: GetObjectResponseSchema = regression_model_service.extract_ml_model()
    regression_model_inference_session: InferenceSession = InferenceSession(
        regression_model_response_schema.body.read()
    )
    regression_model_response_schema.metadata = regression_model_response_schema.eval_metadata(
        metadata=regression_model_inference_session.get_modelmeta().custom_metadata_map
    )

    for rank in range(1, int(regression_model_response_schema.metadata["range"])):
        for multiplier in regression_model_response_schema.metadata[f"{rank}_multipliers"]:
            ohlc = weighted_average_by(
                dataframe=ohlc,
                multiplier=multiplier,
                weights=regression_model_response_schema.metadata[f"{rank}_weights"],
            )
            logger.info(f"Regression {multiplier}-multiplier is ready.")

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
        finalize_trades=True,
        exclusive_orders=True,
        **BacktestParametersSchema().model_dump(),
    )

    # pylint: disable=protected-access
    test._strategy.regression_model_inference_session = regression_model_inference_session
    test._strategy.regression_model_response_schema = regression_model_response_schema
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
