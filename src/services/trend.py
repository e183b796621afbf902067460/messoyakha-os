from typing import Any, Literal

from backtesting import Backtest, Strategy
from numpy import array, ceil, float32, ndarray
from onnxruntime import InferenceSession
from pandas import DataFrame, Series
from talib import SAREXT

from src.schemas.backtests import BacktestParametersSchema
from src.schemas.domain.s3 import GetObjectResponseSchema
from src.schemas.trials import SARParametersSchema

MA: Literal["kama_4"] = "kama_4"


class _MLStrategy(Strategy):

    # pylint: disable=attribute-defined-outside-init
    def init(self) -> None:
        self._risk_model_inference_session: InferenceSession
        self._risk_model_response_schema: GetObjectResponseSchema

        self._exposure_model_inference_session: InferenceSession
        self._exposure_model_response_schema: GetObjectResponseSchema

        self._duration: int = 0

    # pylint: enable=attribute-defined-outside-init

    def next(self) -> None:
        ...

    @property
    def _risk_inference_features(self) -> ndarray:
        return array(  # type: ignore[no-any-return]
            [[self.data[column][-1] for column in self.risk_model_response_schema.metadata["columns"]]],
            dtype=float32,
        )

    @property
    def risk_model_inference_session(self) -> InferenceSession:
        return self._risk_model_inference_session

    @property
    def risk_model_response_schema(self) -> GetObjectResponseSchema:
        return self._risk_model_response_schema

    def _estimate_risk(self) -> int:
        inference: dict[int, float] = self.risk_model_inference_session.run(
            None, input_feed={"input": self._risk_inference_features}
        )[1][0]
        return 0 if inference[0] > inference[1] else 1

    @property
    def _exposure_inference_features(self) -> ndarray:
        return array(  # type: ignore[no-any-return]
            [[self.data[column][-1] for column in self.exposure_model_response_schema.metadata["columns"]]],
            dtype=float32,
        )

    @property
    def exposure_model_inference_session(self) -> InferenceSession:
        return self._exposure_model_inference_session

    @property
    def exposure_model_response_schema(self) -> GetObjectResponseSchema:
        return self._exposure_model_response_schema

    def _estimate_exposure(self) -> float:
        return float(
            self.exposure_model_inference_session.run(None, input_feed={"input": self._exposure_inference_features})[0][
                0
            ][0]
        )


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


class _MLBullishTrendStrategy(_MLStrategy, _BullishTrendStrategy):
    @property
    def _ma_high_on_bull_market(self) -> Any:
        return self._data[f"{self.ma_on_bull_market_prefix}_high"]

    def init(self) -> None:
        _MLStrategy.init(self=self)

    # pylint: disable=protected-access, attribute-defined-outside-init
    def next(self) -> None:
        if self.position.is_long:
            self._duration += 1
            for trade in self._broker.trades:
                trade.sl = self._sar_on_bull_market[-1]

        if self._is_bull_reversal():
            self.position.close()
            for order in self._broker.orders:
                order.cancel()
            risk: int = self._estimate_risk()
            if risk:
                exposure: float = self._estimate_exposure()
                size: int = int(ceil(self._broker._cash * exposure / self.data.Close[-1]))  # noqa: WPS432
                self.buy(size=size * 5, tag=self._broker._cash)
                self._duration = 1

    # pylint: enable=protected-access, attribute-defined-outside-init


class _MLBearishTrendStrategy(_MLStrategy, _BearishTrendStrategy):
    @property
    def _ma_low_on_bear_market(self) -> Any:
        return self._data[f"{self.ma_on_bear_market_prefix}_low"]

    def init(self) -> None:
        _MLStrategy.init(self=self)

    # pylint: disable=protected-access, attribute-defined-outside-init
    def next(self) -> None:
        if self.position.is_short:
            self._duration += 1
            for trade in self._broker.trades:
                trade.sl = self._sar_on_bear_market[-1]

        if self._is_bear_reversal():
            self.position.close()
            for order in self._broker.orders:
                order.cancel()
            risk: int = self._estimate_risk()
            if risk:
                exposure: float = self._estimate_exposure()
                size: int = int(ceil(self._broker._cash * exposure / self.data.Close[-1]))  # noqa: WPS432
                self.sell(size=size * 5, tag=self._broker._cash)
                self._duration = 1

    # pylint: enable=protected-access, attribute-defined-outside-init


class TrendStrategy(_BullishTrendStrategy, _BearishTrendStrategy):
    def init(self) -> None:
        _BullishTrendStrategy.init(self=self)
        _BearishTrendStrategy.init(self=self)

    def next(self) -> None:
        _BullishTrendStrategy.next(self=self)
        _BearishTrendStrategy.next(self=self)


# pylint: disable=too-many-ancestors, attribute-defined-outside-init
class MLTrendStrategy(_MLBullishTrendStrategy, _MLBearishTrendStrategy):
    def init(self) -> None:
        _MLBullishTrendStrategy.init(self=self)
        _MLBearishTrendStrategy.init(self=self)

        self._sar: ndarray = self._sar_on_bull_market or self._sar_on_bear_market
        self._sar_scatter: ndarray = self.I(
            lambda value: value, self._sar, scatter=True, overlay=True, name="SAR", color="black"
        )

    def next(self) -> None:
        _MLBullishTrendStrategy.next(self=self)
        _MLBearishTrendStrategy.next(self=self)


# pylint: enable=too-many-ancestors, attribute-defined-outside-init


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
