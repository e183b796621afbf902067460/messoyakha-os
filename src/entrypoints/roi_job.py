# pylint: disable=duplicate-code
from typing import Final
from uuid import uuid1
from warnings import filterwarnings

from boto3 import Session
from duckdb import DuckDBPyConnection
from loguru import logger
from pandas import DataFrame, Series, concat, to_datetime  # noqa: WPS347

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.indicators import MARepository
from src.adapters.repositories.trades import TradesRepository
from src.adapters.repositories.trials import SARTrialsRepository
from src.schemas.filters import (
    MAPathParametersSchema,
    MAQueryParametersSchema,
    OHLCPathParametersSchema,
    OHLCQueryParametersSchema,
    SARTrialPathParametersSchema,
    SARTrialQueryParametersSchema,
    TradePathParametersSchema,
    TradeQueryParametersSchema,
)
from src.schemas.trials import SARParametersSchema
from src.services.domain.s3 import MAService, OHLCService, ROIService, SARService
from src.services.trend import backtest
from src.settings import settings

filterwarnings("ignore")

_QUANTILE_THRESHOLD: Final[float] = 0.8

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
    roi_service: ROIService = ROIService(
        s3_client=s3_client,
        repository=TradesRepository(connection=duckdb_connection),
        query_parameters=TradeQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path_parameters=TradePathParametersSchema(bucket=settings.S3_BUCKET, directory="trades"),
    )

    ohlc: DataFrame | None = ohlc_service.extract_ohlc()
    if ohlc is None:
        raise FileNotFoundError("There is no moving averages data.")
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

    ohlc = ohlc.merge(right=moving_averages, how="left", on=["exchange", "section", "ticker", "interval", "datetime"])
    ohlc["datetime"] = to_datetime(ohlc["datetime"])
    ohlc["year"] = ohlc["datetime"].dt.year
    ohlc.set_index(keys="datetime", inplace=True)

    trials: DataFrame | None = sar_service.extract_sar()
    if trials is None:
        raise FileNotFoundError("There is no trials data.")
    trials.drop_duplicates(inplace=True)

    quantile_metric: float = trials["value"].quantile(_QUANTILE_THRESHOLD)
    logger.info(f"Quantile metric is {quantile_metric}.")

    trials.query(f"value > {quantile_metric}", inplace=True)
    logger.info(f"Total unique parameters number is {len(trials)}.")

    trades: list[DataFrame] | DataFrame = []
    for row in trials.itertuples():
        parameters_schema: SARParametersSchema = SARParametersSchema(**row._asdict())
        statistics: Series = backtest(data=ohlc, parameters_schema=parameters_schema)
        statistics["_trades"]["Ticks"] = statistics["_trades"]["ExitBar"] - statistics["_trades"]["EntryBar"]
        statistics["_trades"]["IsLong"] = (statistics["_trades"]["Size"] > 0).astype(int)
        trades.append(statistics["_trades"][["EntryTime", "ReturnPct", "Ticks", "IsLong"]])

        cagr: float = statistics.iloc[11] / 10**2  # noqa: WPS432
        drawdown: float = statistics.iloc[17] / 10**2  # noqa: WPS432

        logger.info(f"Metric is {cagr / abs(drawdown)}.")

    trades = concat(trades)
    trades.sort_values(by="ReturnPct", ascending=True, inplace=True)
    trades.drop_duplicates(subset="EntryTime", keep="first", inplace=True)
    trades.rename(
        mapper={"ReturnPct": "pct", "IsLong": "is_long", "Ticks": "ticks", "EntryTime": "datetime"},
        axis=1,
        inplace=True,
    )

    trades["exchange"] = settings.EXCHANGE
    trades["section"] = settings.SECTION
    trades["ticker"] = settings.TICKER
    trades["interval"] = settings.INTERVAL

    roi_service.load_roi(dataframe=trades, filename=f"{uuid1()}.parquet")
    roi_service.delete_object()


# pylint: enable=duplicate-code
