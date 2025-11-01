from backtesting import Backtest
from pandas import DataFrame, Series
from talib import SAREXT

from src.schemas.backtests import BacktestParametersSchema
from src.schemas.trend import KAMA_SIXTY_FOUR, SARParametersSchema
from src.services.trend import TrendStrategy


def main(data: DataFrame, parameters_schema: SARParametersSchema) -> Series:
    data["sar"] = SAREXT(
        high=data[f"{KAMA_SIXTY_FOUR}_high"],
        low=data[f"{KAMA_SIXTY_FOUR}_low"],
        **parameters_schema.model_dump(by_alias=True),
    )
    data["sar"] = abs(data["sar"])

    backtest: Backtest = Backtest(
        data=data,
        strategy=TrendStrategy,
        trade_on_close=True,
        hedging=False,
        finalize_trades=False,
        exclusive_orders=True,
        **BacktestParametersSchema().model_dump(),
    )
    statistics: Series = backtest.run(
        sar_on_bull_market_prefix="sar",
        ma_on_bull_market_prefix=KAMA_SIXTY_FOUR,
        sar_on_bear_market_prefix="sar",
        ma_on_bear_market_prefix=KAMA_SIXTY_FOUR,
    )
    return statistics
