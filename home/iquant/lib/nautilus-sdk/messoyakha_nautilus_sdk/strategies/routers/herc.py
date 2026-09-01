from nautilus_trader.core.data import Data
from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model.identifiers import InstrumentId


@customdataclass
class CapitalDeploymentData(Data):
    ticker: str
    product: str
    venue: str
    currency: str

    @property
    def nautilus_instrument_id(self) -> InstrumentId:
        return InstrumentId.from_str(f"{self.id}.{self.venue}")
