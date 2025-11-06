from typing import Any, Literal

from backtesting import Backtest, Strategy
from numpy import ceil
from pandas import DataFrame, Series
from talib import SAREXT

from src.schemas.backtests import BacktestParametersSchema
from src.schemas.trials import SARParametersSchema

MA: Literal["kama_256"] = "kama_256"


class _BullishTrendStrategy(Strategy):

    sar_on_bull_market_prefix: str | None = None
    ma_on_bull_market_prefix: str | None = None

    def init(self) -> None:
        ...

    @property
    def _sar_on_bull_market(self) -> Any:
        return self._data[self.sar_on_bull_market_prefix]

    @property
    def _ma_low_on_bull_market(self) -> Any:
        return self._data[f"{self.ma_on_bull_market_prefix}_low"]

    def _is_bull_reversal(self) -> bool:
        return bool(
            self._ma_low_on_bull_market[-1] > self._sar_on_bull_market[-1]
            and self._ma_low_on_bull_market[-2] < self._sar_on_bull_market[-2]
        )

    # pylint: disable=protected-access
    def next(self) -> None:
        if self._is_bull_reversal() and not self.position.is_long:
            self.position.close()
            size: int = int(ceil(self._broker._cash * 0.8 / self.data.Close[-1]))  # noqa: WPS432
            try:
                self.buy(size=size)
            except ValueError:
                ...  # noqa: WPS428

    # pylint: enable=protected-access


class _BearishTrendStrategy(Strategy):

    sar_on_bear_market_prefix: str | None = None
    ma_on_bear_market_prefix: str | None = None

    def init(self) -> None:
        ...

    @property
    def _sar_on_bear_market(self) -> Any:
        return self._data[self.sar_on_bear_market_prefix]

    @property
    def _ma_high_on_bear_market(self) -> Any:
        return self._data[f"{self.ma_on_bear_market_prefix}_high"]

    def _is_bear_reversal(self) -> bool:
        return bool(
            self._ma_high_on_bear_market[-1] < self._sar_on_bear_market[-1]
            and self._ma_high_on_bear_market[-2] > self._sar_on_bear_market[-2]
        )

    # pylint: disable=protected-access
    def next(self) -> None:
        if self._is_bear_reversal() and not self.position.is_short:
            self.position.close()
            size: int = int(ceil(self._broker._cash * 0.8 / self.data.Close[-1]))  # noqa: WPS432
            try:
                self.sell(size=size)
            except ValueError:
                ...  # noqa: WPS428

    # pylint: enable=protected-access


class TrendStrategy(_BullishTrendStrategy, _BearishTrendStrategy):
    def init(self) -> None:
        _BullishTrendStrategy.init(self=self)
        _BearishTrendStrategy.init(self=self)

    def next(self) -> None:
        _BullishTrendStrategy.next(self=self)
        _BearishTrendStrategy.next(self=self)


def backtest(data: DataFrame, parameters_schema: SARParametersSchema) -> Series:
    data["sar"] = SAREXT(
        high=data[f"{MA}_high"],
        low=data[f"{MA}_low"],
        **parameters_schema.model_dump(by_alias=True),
    )
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
    statistics: Series = test.run(
        sar_on_bull_market_prefix="sar",
        ma_on_bull_market_prefix=MA,
        sar_on_bear_market_prefix="sar",
        ma_on_bear_market_prefix=MA,
    )
    return statistics
