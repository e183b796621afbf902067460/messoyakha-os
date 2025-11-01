# pylint: disable=duplicate-code
from secrets import randbelow
from uuid import uuid1

from boto3 import Session
from duckdb import DuckDBPyConnection
from pandas import DataFrame, Series, concat, to_datetime  # noqa: WPS347

from src.adapters.clients.s3 import S3Client
from src.adapters.repositories.common.duckdb_base import get_duckdb_connection
from src.adapters.repositories.moving_average import MARepository
from src.adapters.repositories.ohlc import OHLCRepository
from src.adapters.repositories.stop_and_reverse_trial import SARTrialRepository
from src.adapters.repositories.trade import TradeRepository
from src.entrypoints.commmon.trend_backtest_base import main as backtest
from src.schemas.domain.s3 import ListObjectsResponseSchema
from src.schemas.queries import MAQueryParametersSchema, OHLCQueryParametersSchema, SARTrialQueryParametersSchema
from src.schemas.trend import SARParametersSchema
from src.services.common.misc import format_s3_key, format_s3_path
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
    ohlc_repository: OHLCRepository = OHLCRepository(connection=duckdb_connection)
    ma_repository: MARepository = MARepository(connection=duckdb_connection)
    sar_trial_repository: SARTrialRepository = SARTrialRepository(connection=duckdb_connection)
    trade_repository: TradeRepository = TradeRepository(connection=duckdb_connection)

    s3_ohlc_path: str = format_s3_path(exchange=settings.EXCHANGE, section=settings.SECTION, directory="candlesticks")
    s3_ma_path: str = format_s3_path(exchange=settings.EXCHANGE, section=settings.SECTION, directory="moving-averages")
    s3_sar_trials_path: str = format_s3_path(
        exchange=settings.EXCHANGE, section=settings.SECTION, directory="stop-and-reverse-trials"
    )
    s3_trade_path: str = format_s3_path(exchange=settings.EXCHANGE, section=settings.SECTION, directory="trades")
    list_ohlc_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="candlesticks"),
    )
    list_ma_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="moving-averages"),
    )
    list_sar_trial_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="stop-and-reverse-trials"),
    )
    list_trade_objects_response: ListObjectsResponseSchema = s3_client.list_objects(
        bucket=settings.S3_BUCKET,
        prefix=format_s3_key(exchange=settings.EXCHANGE, section=settings.SECTION, directory="trades"),
    )

    ohlc: DataFrame | None = ohlc_repository.query_candlesticks(
        parameters_schema=OHLCQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path=(
            f"{s3_ohlc_path}/{list_ohlc_objects_response.filename}"
            if list_ohlc_objects_response.filename
            else f"{s3_ohlc_path}/"
        ),
    )
    if ohlc is None:
        raise FileNotFoundError(f"There is no moving averages data in {s3_ohlc_path}.")
    ohlc.rename(
        mapper={"open": "Open", "high": "High", "low": "Low", "close": "Close", "open_time": "datetime"},
        axis=1,
        inplace=True,
    )
    ohlc.drop(columns=["close_time"], axis=1, inplace=True)
    ohlc.drop_duplicates(inplace=True)

    moving_averages: DataFrame | None = ma_repository.query_moving_averages(
        parameters_schema=MAQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path=(
            f"{s3_ma_path}/{list_ma_objects_response.filename}"
            if list_ma_objects_response.filename
            else f"{s3_ma_path}/"
        ),
    )
    if moving_averages is None:
        raise FileNotFoundError(f"There is no moving averages data in {s3_ma_path}.")
    moving_averages.drop_duplicates(inplace=True)

    ohlc = ohlc.merge(right=moving_averages, how="left", on=["exchange", "section", "ticker", "interval", "datetime"])
    ohlc["datetime"] = to_datetime(ohlc["datetime"])
    ohlc["year"] = ohlc["datetime"].dt.year
    ohlc.set_index(keys="datetime", inplace=True)

    stop_and_reverse_trials: DataFrame | None = sar_trial_repository.query_stop_and_reverse_trials(
        parameters_schema=SARTrialQueryParametersSchema(
            ticker=settings.TICKER, exchange=settings.EXCHANGE, section=settings.SECTION, interval=settings.INTERVAL
        ),
        path=(
            f"{s3_sar_trials_path}/{list_sar_trial_objects_response.filename}"
            if list_sar_trial_objects_response.filename
            else f"{s3_sar_trials_path}/"
        ),
    )
    if stop_and_reverse_trials is None:
        raise FileNotFoundError(f"There is no trials data in {s3_sar_trials_path}.")
    stop_and_reverse_trials.drop_duplicates(inplace=True)

    top_percentile: int = int(0.025 * len(stop_and_reverse_trials))  # noqa: WPS432
    stochastic_parameters_indexes: list[int] = [
        randbelow(exclusive_upper_bound=top_percentile) for _ in range(int(top_percentile * 0.05))  # noqa: WPS432
    ]

    trades: list[DataFrame] | DataFrame = []
    for stochastic_parameters_index in stochastic_parameters_indexes:
        parameters_schema: SARParametersSchema = SARParametersSchema(
            **stop_and_reverse_trials.iloc[stochastic_parameters_index].to_dict()
        )
        statistics: Series = backtest(data=ohlc, parameters_schema=parameters_schema)
        statistics["_trades"]["Ticks"] = statistics["_trades"]["ExitBar"] - statistics["_trades"]["EntryBar"]
        trades.append(statistics["_trades"][["EntryTime", "ReturnPct", "Ticks"]])
    trades = concat(trades)
    trades.sort_values(by="ReturnPct", ascending=False)
    trades.drop_duplicates(subset="EntryTime", keep="first", inplace=True)
    trades.rename(
        mapper={"ReturnPct": "pct", "Ticks": "ticks", "EntryTime": "datetime"},
        axis=1,
        inplace=True,
    )

    trade_repository.insert_dataframe_as_parquet(dataframe=trades, key=f"{s3_trade_path}/{uuid1()}.parquet")
    if list_trade_objects_response.filename:
        s3_client.delete_object(
            bucket=settings.S3_BUCKET,
            key=format_s3_key(
                exchange=settings.EXCHANGE,
                section=settings.SECTION,
                directory="trades",
                filename=list_trade_objects_response.filename,
            ),
        )


# pylint: enable=duplicate-code
