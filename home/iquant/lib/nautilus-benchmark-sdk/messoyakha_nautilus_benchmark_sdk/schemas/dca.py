from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.objects import Currency


class DCAConfig(StrategyConfig, frozen=True):
    id: InstrumentId
    venue: Venue
    currency: Currency

    bars: BarType
