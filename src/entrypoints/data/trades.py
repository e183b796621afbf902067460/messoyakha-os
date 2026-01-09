# pylint: disable=duplicate-code
from typing import Final
from uuid import uuid1
from warnings import filterwarnings

from backtesting import Backtest
from boto3 import Session
from duckdb import DuckDBPyConnection
from loguru import logger
from pandas import DataFrame, Series, concat, to_datetime  # noqa: WPS347
from pydantic import BaseModel
from talib import SAREXT

from src.adapters.clients.s3 import S3Client
from src.adapters.connections.duckdb import get_duckdb_connection
from src.adapters.repositories.candlesticks import CandlesticksRepository
from src.adapters.repositories.indicators import MARepository
from src.adapters.repositories.trades import TradesRepository
from src.adapters.repositories.trials import SARTrialsRepository
from src.schemas.backtests import BacktestParametersSchema
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
from src.services.domain.s3 import EVService, MAService, OHLCService, SARService
from src.services.trends import TrendStrategy
from src.settings import settings

filterwarnings("ignore")

_THRESHOLD: Final[float] = 0.8


class _MainSchema(BaseModel):
    ohlc_service: OHLCService
    ma_service: MAService
    sar_service: SARService
    ev_service: EVService

    class Config:
        arbitrary_types_allowed = True


# pylint: disable=too-many-statements
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

    data: DataFrame = main_schema.ohlc_service.ohlc.merge(
        right=main_schema.ma_service.ma, how="left", on=["exchange", "section", "ticker", "interval", "datetime"]
    )
    data["datetime"] = to_datetime(data["datetime"])
    data["year"] = data["datetime"].dt.year
    data.set_index(keys="datetime", inplace=True)

    if main_schema.sar_service.sar_trials is None:
        raise FileNotFoundError("There is no trials data.")

    thresholded_metric: float = main_schema.sar_service.sar_trials["value"].quantile(_THRESHOLD)
    logger.info(f"Thresholded lowest metric is {thresholded_metric}.")

    main_schema.sar_service.sar_trials.query(f"value > {thresholded_metric}", inplace=True)
    logger.info(f"Total unique parameters number is {len(main_schema.sar_service.sar_trials)}.")

    trades: list[DataFrame] | DataFrame = []
    for sar_trial in main_schema.sar_service.sar_trials.itertuples():
        parameters: SARParametersSchema = SARParametersSchema(**sar_trial._asdict())
        data["sar"] = SAREXT(high=data["High"], low=data["Low"], **parameters.model_dump(by_alias=True))
        data["sar"] = abs(data["sar"])
        test: Backtest = Backtest(
            data=data,
            strategy=TrendStrategy,
            trade_on_close=True,
            hedging=False,
            finalize_trades=False,
            exclusive_orders=True,
            **BacktestParametersSchema().model_dump(),
        )
        statistics: Series = test.run()
        statistics["_trades"]["Ticks"] = (  # noqa: WPS204
            statistics["_trades"]["ExitBar"] - statistics["_trades"]["EntryBar"]
        )
        statistics["_trades"]["IsLong"] = (statistics["_trades"]["Size"] > 0).astype(int)
        trades.append(statistics["_trades"][["EntryTime", "ReturnPct", "Ticks", "IsLong"]])

        cagr: float = statistics.iloc[11] / 10**2  # noqa: WPS432
        drawdown: float = statistics.iloc[17] / 10**2  # noqa: WPS432
        logger.info(f"Metric is {cagr / abs(drawdown):.2f}.")

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

    main_schema.ev_service.load_ev(dataframe=trades, filename=f"{uuid1()}.parquet")
    main_schema.ev_service.delete_object()


# pylint: enable=too-many-statements


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
        )
    )


# pylint: enable=duplicate-code
