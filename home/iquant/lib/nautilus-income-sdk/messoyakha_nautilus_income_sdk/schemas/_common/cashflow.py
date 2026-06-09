from nautilus_trader.core.data import Data
from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model.objects import Currency


@customdataclass
class CashflowData(Data):
    flow: float
    currency: str

    @property
    def nautilus_currency(self) -> Currency:
        return Currency.from_str(self.currency)
