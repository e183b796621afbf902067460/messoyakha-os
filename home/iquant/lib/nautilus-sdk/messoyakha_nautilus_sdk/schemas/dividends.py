from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model.identifiers import InstrumentId

from messoyakha_nautilus_sdk.schemas._common.income import IncomeData


@customdataclass
class DividendIncomeData(IncomeData):
    id: str
    venue: str

    @property
    def nautilus_instrument_id(self) -> InstrumentId:
        return InstrumentId.from_str(f"{self.id}.{self.venue}")
