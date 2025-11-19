from typing import Any, Literal

from backtesting import Backtest, Strategy
from numpy import array, ceil, float32, ndarray
from onnxruntime import InferenceSession
from pandas import DataFrame, Series
from talib import SAREXT

from src.schemas.backtests import BacktestParametersSchema
from src.schemas.domain.s3 import GetObjectResponseSchema
from src.schemas.trials import SARParametersSchema

MA: Literal["kama_64"] = "kama_64"


def _leverage(risk: float) -> int:
    if 0.5 <= risk < 0.625:  # noqa: WPS432
        return 2
    if 0.625 <= risk < 0.75:  # noqa: WPS432
        return 4
    if 0.75 <= risk < 0.875:  # noqa: WPS432
        return 4
    return 2


class _MLStrategy(Strategy):

    # pylint: disable=attribute-defined-outside-init
    def init(self) -> None:
        self._ml_model_inference_session: InferenceSession
        self._ml_model_response_schema: GetObjectResponseSchema

    # pylint: enable=attribute-defined-outside-init

    def next(self) -> None:
        ...

    @property
    def _inference_features(self) -> ndarray:
        return array(  # type: ignore[no-any-return]
            [[self.data[column][-1] for column in self.ml_model_response_schema.metadata["columns"]]], dtype=float32
        )

    @property
    def ml_model_inference_session(self) -> InferenceSession:
        return self._ml_model_inference_session

    @property
    def ml_model_response_schema(self) -> GetObjectResponseSchema:
        return self._ml_model_response_schema


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


class _MLBullishTrendStrategy(_MLStrategy, _BullishTrendStrategy):
    def init(self) -> None:
        _MLStrategy.init(self=self)

    # pylint: disable=protected-access
    def next(self) -> None:
        if self._is_bull_reversal() and not self.position.is_long:
            self.position.close()

            risk: float = float(
                self.ml_model_inference_session.run(None, input_feed={"input": self._inference_features})[0][0][0]
            )
            leverage: int = _leverage(risk=risk)
            size: int = int(ceil(self._broker._cash * risk / self.data.Close[-1]))  # noqa: WPS432

            if risk > 0.5:
                try:
                    self.buy(size=size * leverage)
                except ValueError:
                    ...  # noqa: WPS428
            else:
                self.sell(size=size)

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


class _MLBearishTrendStrategy(_MLStrategy, _BearishTrendStrategy):
    def init(self) -> None:
        _MLStrategy.init(self=self)

    # pylint: disable=protected-access
    def next(self) -> None:
        if self._is_bear_reversal() and not self.position.is_short:
            self.position.close()

            risk: float = float(
                self.ml_model_inference_session.run(None, input_feed={"input": self._inference_features})[0][0][0]
            )
            leverage: int = _leverage(risk=risk)
            size: int = int(ceil(self._broker._cash * risk / self.data.Close[-1]))  # noqa: WPS432

            if risk > 0.5:
                try:
                    self.sell(size=size * leverage)
                except ValueError:
                    ...  # noqa: WPS428
            else:
                self.buy(size=size)

    # pylint: enable=protected-access


class TrendStrategy(_BullishTrendStrategy, _BearishTrendStrategy):
    def init(self) -> None:
        _BullishTrendStrategy.init(self=self)
        _BearishTrendStrategy.init(self=self)

    def next(self) -> None:
        _BullishTrendStrategy.next(self=self)
        _BearishTrendStrategy.next(self=self)


# pylint: disable=too-many-ancestors
class MLTrendStrategy(_MLBullishTrendStrategy, _MLBearishTrendStrategy):
    def init(self) -> None:
        _MLBullishTrendStrategy.init(self=self)
        _MLBearishTrendStrategy.init(self=self)

    def next(self) -> None:
        _MLBullishTrendStrategy.next(self=self)
        _MLBearishTrendStrategy.next(self=self)


# pylint: enable=too-many-ancestors


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
