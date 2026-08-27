from typing import Self

from nautilus_trader.core.data import Data
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model.objects import Currency
from pandas import DataFrame, Timestamp


@customdataclass
class IncomeData(Data):
    income: float
    currency: str

    @property
    def nautilus_currency(self) -> Currency:
        return Currency.from_str(self.currency)

    @classmethod
    def _from_params(cls, income: float, currency: str, timestamp: Timestamp, *args, **kwargs) -> Self:
        ts: int = dt_to_unix_nanos(dt=timestamp)

        data: Self = cls(income=income, currency=currency, **kwargs)
        data._ts_event = ts
        data._ts_init = ts
        return data

    @staticmethod
    def from_pandas(data: DataFrame) -> list[Self]:
        incomes: list[Self] = [
            IncomeData._from_params(**row._asdict())  # type: ignore[not-callable]
            for row in data.itertuples()
        ]
        return incomes
