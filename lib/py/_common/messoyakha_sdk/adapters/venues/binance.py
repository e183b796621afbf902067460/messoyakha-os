from typing import Final

from nautilus_trader.adapters.binance.common.constants import (
    BINANCE as _BINANCE,
    BINANCE_CLIENT_ID as _BINANCE_CLIENT_ID,
    BINANCE_VENUE as _BINANCE_VENUE,
)
from nautilus_trader.model.identifiers import ClientId, Venue


BINANCE: Final[str] = _BINANCE

BINANCE_VENUE: Final[Venue] = _BINANCE_VENUE
BINANCE_CLIENT_ID: Final[ClientId] = _BINANCE_CLIENT_ID
