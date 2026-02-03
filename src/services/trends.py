from abc import abstractmethod

from backtesting import Strategy
from catboost import CatBoostRegressor
from numpy import ceil, ndarray
from pandas import DataFrame

from src.services.f import f, r


class _MLStrategy(Strategy):

    # pylint: disable=attribute-defined-outside-init
    def init(self) -> None:
        self._ma_prefixes: list[str]

        self._ml_model: CatBoostRegressor

        self._ml_model_adx_columns: list[str] = eval(self.ml_model.get_metadata()["adx_columns"])
        self._ml_model_categorical_columns: list[str] = eval(self.ml_model.get_metadata()["categorical_columns"])
        self._ml_model_feature_columns: list[str] = eval(self.ml_model.get_metadata()["feature_columns"])

        self._duration: int = 0

        self._is_bullish_signal: bool = False
        self._is_bearish_signal: bool = False

    # pylint: enable=attribute-defined-outside-init

    def next(self) -> None:
        ...

    @property
    @abstractmethod
    def is_long(self) -> int:
        raise NotImplementedError

    @property
    def ma_prefixes(self) -> list[str]:
        return self._ma_prefixes

    @property
    def ml_model(self) -> CatBoostRegressor:
        return self._ml_model

    @property
    def _ml_features(self) -> DataFrame:
        data: DataFrame | None = self.data.df.iloc[[-1]]
        data["is_long"] = self.is_long

        data = f(
            data=data,
            ma_prefixes=self.ma_prefixes,
            adx_columns=self._ml_model_adx_columns, categorical_columns=self._ml_model_categorical_columns
        )
        return data[self._ml_model_feature_columns] if isinstance(data, DataFrame) else data

    def _ml_inference(self) -> float | None:
        features: DataFrame | float | None = self._ml_features
        return float(self.ml_model.predict(data=features)[0]) if isinstance(features, DataFrame) else features

    def _random_inference(self) -> float | None:
        data: DataFrame = self.data.df.iloc[[-1]]
        data["is_long"] = self.is_long
        return r(
            data=data,
            ma_prefixes=self.ma_prefixes,
            adx_columns=self._ml_model_adx_columns
        )


class _BullishTrendStrategy(Strategy):
    def init(self) -> None:
        ...

    def _is_bull_reversal(self) -> bool:
        return bool(self.data.Low[-1] > self._data["sar"][-1] and self.data.Low[-2] < self._data["sar"][-2])

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
    def init(self) -> None:
        ...

    def _is_bear_reversal(self) -> bool:
        return bool(self.data.High[-1] < self._data["sar"][-1] and self.data.High[-2] > self._data["sar"][-2])

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
    def init(self) -> None:
        _MLStrategy.init(self=self)

    @property
    def is_long(self) -> int:
        return 1

    # pylint: disable=protected-access, attribute-defined-outside-init
    def next(self) -> None:
        if self.position.is_long:
            self._duration += 1

        if self._is_bull_reversal():
            self.position.close()
            for order in self._broker.orders:
                order.cancel()
            exposure: float | None = self._ml_inference()
            if exposure:
                size: int = int(ceil(self._broker._cash * exposure / self.data.Close[-1]))  # noqa: WPS432
                self.buy(size=size, tag=exposure)
                self._duration = 1

    # pylint: enable=protected-access, attribute-defined-outside-init


class _MLBearishTrendStrategy(_MLStrategy, _BearishTrendStrategy):
    def init(self) -> None:
        _MLStrategy.init(self=self)

    @property
    def is_long(self) -> int:
        return 0

    # pylint: disable=protected-access, attribute-defined-outside-init
    def next(self) -> None:
        if self.position.is_short:
            self._duration += 1

        if self._is_bear_reversal():
            self.position.close()
            for order in self._broker.orders:
                order.cancel()
            exposure: float = self._ml_inference()
            if exposure:
                size: int = int(ceil(self._broker._cash * exposure / self.data.Close[-1]))  # noqa: WPS432
                self.sell(size=size, tag=exposure)
                self._duration = 1

    # pylint: enable=protected-access, attribute-defined-outside-init


class TrendStrategy(_BullishTrendStrategy, _BearishTrendStrategy):
    def init(self) -> None:
        _BullishTrendStrategy.init(self=self)
        _BearishTrendStrategy.init(self=self)

    def next(self) -> None:
        if self._is_bear_reversal() or self._is_bull_reversal():
            self.position.close()
        _BullishTrendStrategy.next(self=self)
        _BearishTrendStrategy.next(self=self)


# pylint: disable=too-many-ancestors, attribute-defined-outside-init
class MLTrendStrategy(_MLBullishTrendStrategy, _MLBearishTrendStrategy):
    def init(self) -> None:
        _MLBullishTrendStrategy.init(self=self)
        _MLBearishTrendStrategy.init(self=self)

        self._sar_scatter: ndarray = self.I(
            lambda value: value, self._data["sar"], scatter=True, overlay=True, name="SAR", color="black"
        )

    def next(self) -> None:
        if self._is_bear_reversal() or self._is_bull_reversal():
            self.position.close()
        _MLBullishTrendStrategy.next(self=self)
        _MLBearishTrendStrategy.next(self=self)


# pylint: enable=too-many-ancestors, attribute-defined-outside-init
